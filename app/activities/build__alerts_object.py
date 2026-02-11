from typing import Any, Dict, List, Tuple, Optional, DefaultDict
from collections import defaultdict
import re
from pathlib import Path
from temporalio import activity
from app.models.models import (
    ManifestRef, SecurityAlertRef, SecurityAlertSummary, RepositorySecuritySummary, OrgSecuritySummary
)

def _parse_version(version_str: str) -> Tuple[List[int], str]:
    """Parse version string into comparable parts. Returns tuple of (numeric_parts, original_string)."""
    v = version_str.lstrip('v')
    parts = []
    for part in v.split('.'):
        numeric = ''
        for char in part:
            if char.isdigit():
                numeric += char
            else:
                break
        if numeric:
            parts.append(int(numeric))
        else:
            parts.append(0)
    return (parts, version_str)

def _safe_max_version(versions: List[str]) -> Optional[str]:
    """Return highest version using simple numeric comparison; ignore invalid entries."""
    if not versions:
        return None
    parsed = []
    for v in versions:
        try:
            parsed.append(_parse_version(v))
        except Exception:
            continue
    if not parsed:
        return None
    parsed.sort(key=lambda t: t[0])
    return parsed[-1][1]

def _extract_version_from_description(description: str) -> Optional[str]:
    """
    Extract version number from advisory description for virtualenv-like cases.
    Looks for patterns like "Versions with the fix: X.Y.Z and later" or "Fixed in: X.Y.Z"
    """
    if not description:
        return None
    
    # Pattern 1: "Versions with the fix: X.Y.Z and later"
    match = re.search(r'Versions with the fix:\s*(\d+\.\d+\.\d+)\s+and later', description, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 2: "Fixed in: X.Y.Z" or "Fixed in version X.Y.Z"
    match = re.search(r'Fixed in:?\s+(?:version\s+)?(\d+\.\d+\.\d+)', description, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

def _truncate_summary(text: str, max_length: int = 200) -> str:
    """Truncate summary to first sentence or max_length, whichever is shorter."""
    if not text:
        return ""
    
    # Try to find first sentence
    sentence_end = re.search(r'[.!?]\s', text)
    if sentence_end:
        result = text[:sentence_end.end()].strip()
        if len(result) <= max_length:
            return result
    
    # Fallback: truncate at max_length
    if len(text) <= max_length:
        return text.strip()
    
    return text[:max_length].rsplit(' ', 1)[0].strip() + "..."

@activity.defn(name="build_alerts_object_activity")
async def build_alerts_object_activity(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build enhanced security summary with detailed package information and persist to disk.

    Args:
        payload: Dictionary containing:
                {
                    "org": "organization-name",
                    "raw_alerts": [...]  # list of alert dictionaries from fetch_dependabot_alerts_activity
                }

    Returns:
        Dictionary containing results:
        {
            "file_path": "dependabot-remediation-plan/remediation-plan.json",
            "status": "success",
            "repo_count": 5,
            "alert_count": 42
        }
    """
    activity.logger.info("Starting build alerts object activity")

    org = payload.get("org")
    raw_alerts = payload.get("raw_alerts", [])

    if not org:
        raise ValueError("Missing required parameter: org")

    activity.logger.info(
        f"Building remediation plan for org: {org} with {len(raw_alerts)} raw alerts"
    )
    def repo_full_name(alert: Dict[str, Any]) -> str:
        rep = alert.get("repository")
        if isinstance(rep, dict) and rep.get("full_name"):
            return rep["full_name"]
        html = alert.get("html_url") or ""
        parts = html.split("/")
        try:
            idx = parts.index("github.com")
            return f"{parts[idx+1]}/{parts[idx+2]}"
        except Exception:
            api = alert.get("url") or ""
            if "/repos/" in api:
                segs = api.split("/repos/")[1].split("/")
                return f"{segs[0]}/{segs[1]}"
            return "unknown/unknown"

    def repo_html_url(alert: Dict[str, Any]) -> Optional[str]:
        """Extract repository HTML URL from alert."""
        rep = alert.get("repository")
        if isinstance(rep, dict) and rep.get("html_url"):
            return rep["html_url"]
        return None

    # Group alerts by (repo, ecosystem, package)
    grouped: DefaultDict[str, DefaultDict[Tuple[str, str], List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for a in raw_alerts:
        dep = a.get("dependency", {}) or {}
        package = (dep.get("package") or {}).get("name") or "unknown"
        ecosystem = (dep.get("package") or {}).get("ecosystem") or "unknown"
        repo = repo_full_name(a)
        grouped[repo][(ecosystem, package)].append(a)

    repositories: List[RepositorySecuritySummary] = []
    
    for repo_name, pkg_map in grouped.items():
        # Extract short repo name and html_url
        repo_short_name = repo_name.split("/", 1)[1] if "/" in repo_name else repo_name
        repo_url = None
        
        security_alerts: List[SecurityAlertSummary] = []

        for (ecosystem, package), alerts in pkg_map.items():
            # Collect all data from alerts
            manifests_dict: Dict[str, Optional[str]] = {}  # path -> scope
            fix_versions_set: set = set()
            ghsas_set: set = set()
            cves_set: set = set()
            vulnerable_ranges_set: set = set()
            references_set: set = set()
            alert_refs: List[SecurityAlertRef] = []
            cvss_scores: List[float] = []
            severities: List[str] = []
            summaries: List[str] = []
            descriptions: List[str] = []

            for a in alerts:
                # Get repo URL from first alert
                if not repo_url:
                    repo_url = repo_html_url(a)
                
                # Extract per-alert metadata
                sa = a.get("security_advisory") or {}
                sv = a.get("security_vulnerability") or {}
                
                # Per-alert identifiers
                alert_ghsas = []
                alert_cves = []
                for ident in sa.get("identifiers", []) or []:
                    if ident.get("type") == "GHSA" and ident.get("value"):
                        alert_ghsas.append(ident["value"])
                    if ident.get("type") == "CVE" and ident.get("value"):
                        alert_cves.append(ident["value"])
                
                # Per-alert severity
                alert_severity = sa.get("severity")
                
                # Per-alert vulnerable range (prefer security_vulnerability, fallback to advisory)
                alert_vulnerable_range = sv.get("vulnerable_version_range")
                if not alert_vulnerable_range and sa.get("vulnerabilities"):
                    # Take first vulnerability's range
                    vuln_list = sa.get("vulnerabilities", [])
                    if vuln_list and vuln_list[0].get("vulnerable_version_range"):
                        alert_vulnerable_range = vuln_list[0]["vulnerable_version_range"]
                
                # Per-alert summary (truncate)
                alert_summary = None
                if sa.get("summary"):
                    alert_summary = _truncate_summary(sa["summary"])
                elif sa.get("description"):
                    alert_summary = _truncate_summary(sa["description"])
                
                # Create enriched alert reference
                alert_refs.append(SecurityAlertRef(
                    number=int(a.get("number")),
                    html_url=a.get("html_url"),
                    summary=alert_summary,
                    ghsas=alert_ghsas,
                    cves=alert_cves,
                    severity=alert_severity,
                    vulnerable_version_range=alert_vulnerable_range
                ))
                
                # Manifest info with scope
                dep = a.get("dependency", {}) or {}
                if dep.get("manifest_path"):
                    manifests_dict[dep["manifest_path"]] = dep.get("scope")

                # Security advisory data
                sa = a.get("security_advisory") or {}
                if sa:
                    # Identifiers
                    for ident in sa.get("identifiers", []) or []:
                        if ident.get("type") == "GHSA" and ident.get("value"):
                            ghsas_set.add(ident["value"])
                        if ident.get("type") == "CVE" and ident.get("value"):
                            cves_set.add(ident["value"])
                    
                    # Severity
                    if sa.get("severity"):
                        severities.append(sa["severity"])
                    
                    # CVSS
                    cvss = (sa.get("cvss") or {}).get("score")
                    if isinstance(cvss, (float, int)):
                        cvss_scores.append(float(cvss))
                    
                    # Summary and description
                    if sa.get("summary"):
                        summaries.append(sa["summary"])
                    if sa.get("description"):
                        descriptions.append(sa["description"])
                    
                    # References
                    for ref in sa.get("references", []) or []:
                        if ref.get("url"):
                            references_set.add(ref["url"])
                    
                    # Vulnerabilities - get ranges and patched versions
                    for v in sa.get("vulnerabilities", []) or []:
                        if v.get("vulnerable_version_range"):
                            vulnerable_ranges_set.add(v["vulnerable_version_range"])
                        fp = (v.get("first_patched_version") or {}).get("identifier")
                        if fp:
                            fix_versions_set.add(fp)

                # Security vulnerability data (fallback/additional)
                sv = a.get("security_vulnerability") or {}
                if sv:
                    if sv.get("vulnerable_version_range"):
                        vulnerable_ranges_set.add(sv["vulnerable_version_range"])
                    fp = (sv.get("first_patched_version") or {}).get("identifier")
                    if fp:
                        fix_versions_set.add(fp)

            # Parse advisory descriptions for additional fix versions (virtualenv rule)
            for desc in descriptions:
                extracted_version = _extract_version_from_description(desc)
                if extracted_version:
                    fix_versions_set.add(extracted_version)

            # Convert manifests dict to list of ManifestRef
            manifests = [ManifestRef(path=path, scope=scope) for path, scope in manifests_dict.items()]
            
            # Deduplicate and sort fix_versions
            fix_versions = sorted(list(fix_versions_set))
            
            # Determine target_version (highest fix version)
            target_version = None
            if ecosystem.lower() == "pip":
                target_version = _safe_max_version(fix_versions) if fix_versions else None
            else:
                target_version = max(fix_versions) if fix_versions else None

            # Determine severity (use worst if multiple)
            severity_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            severity = None
            if severities:
                severity = max(severities, key=lambda s: severity_priority.get(s.lower(), 0))
            
            # Highest CVSS
            highest_cvss = max(cvss_scores) if cvss_scores else None
            
            # Create concise summary (prefer first summary, truncate)
            summary = None
            if summaries:
                summary = _truncate_summary(summaries[0])
            elif descriptions:
                # Extract first sentence from description as fallback
                summary = _truncate_summary(descriptions[0])
            
            # Sort and limit references (keep top 5 to stay concise)
            references = sorted(list(references_set))[:5]
            
            # Create SecurityAlertSummary
            security_alerts.append(SecurityAlertSummary(
                ecosystem=ecosystem,
                package=package,
                manifests=manifests,
                current_version=None,  # Not available from Dependabot API
                target_version=target_version,
                fix_versions=fix_versions,
                severity=severity,
                highest_cvss=highest_cvss,
                ghsas=sorted(list(ghsas_set)),
                cves=sorted(list(cves_set)),
                vulnerable_ranges=sorted(list(vulnerable_ranges_set)),
                summary=summary,
                references=references,
                alerts=alert_refs
            ))
        
        repositories.append(RepositorySecuritySummary(
            name=repo_short_name,
            html_url=repo_url,
            security_alerts=security_alerts
        ))

    # Build final response
    result = OrgSecuritySummary(
        org=org,
        source="github_dependabot_org_alerts",
        state="open",
        repositories=repositories
    )
    
    # Validate before persisting
    plan_json = result.model_dump_json(indent=2)
    
    # Ensure directory exists (idempotent)
    output_dir = Path("dependabot-remediation-plan")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write to persistent location
    output_file = output_dir / "remediation-plan.json"
    output_file.write_text(plan_json, encoding="utf-8")
    
    # Calculate statistics
    total_alerts = sum(len(repo.security_alerts) for repo in repositories)
    
    activity.logger.info(
        f"Completed: wrote remediation plan to {output_file} "
        f"({len(repositories)} repositories, {total_alerts} unique alerts)"
    )
    
    return {
        "file_path": str(output_file),
        "status": "success",
        "repo_count": len(repositories),
        "alert_count": total_alerts
    }
