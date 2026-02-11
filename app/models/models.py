
from typing import List, Optional, Set, Dict, Any
from pydantic import BaseModel, Field

class ManifestRef(BaseModel):
    """Reference to a manifest file with scope information."""
    path: str
    scope: Optional[str] = None

class SecurityAlertRef(BaseModel):
    """
    Enriched reference to a security alert with per-alert metadata.
    
    For packages with multiple alerts, each alert may have different:
    - Summaries (different vulnerability descriptions)
    - Identifiers (different CVEs/GHSAs)
    - Severity levels
    - Vulnerable version ranges
    """
    number: int
    html_url: str
    summary: Optional[str] = None
    ghsas: List[str] = Field(default_factory=list)
    cves: List[str] = Field(default_factory=list)
    severity: Optional[str] = None
    vulnerable_version_range: Optional[str] = None

class SecurityAlertSummary(BaseModel):
    """Detailed summary for a package's security alerts."""
    ecosystem: str
    package: str
    manifests: List[ManifestRef] = Field(default_factory=list)
    current_version: Optional[str] = None  # Will be populated by future agent logic
    target_version: Optional[str] = None
    fix_versions: List[str] = Field(default_factory=list)
    severity: Optional[str] = None
    highest_cvss: Optional[float] = None
    ghsas: List[str] = Field(default_factory=list)
    cves: List[str] = Field(default_factory=list)
    vulnerable_ranges: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    references: List[str] = Field(default_factory=list)
    alerts: List[SecurityAlertRef] = Field(default_factory=list)

class RepositorySecuritySummary(BaseModel):
    """Security summary for a single repository."""
    name: str
    html_url: Optional[str] = None
    security_alerts: List[SecurityAlertSummary] = Field(default_factory=list)

class OrgSecuritySummary(BaseModel):
    """Top-level organization security summary."""
    org: str
    source: str = "github_dependabot_org_alerts"
    state: str = "open"
    repositories: List[RepositorySecuritySummary] = Field(default_factory=list)

class AgentRemediationResult(BaseModel):
    """Result from a single repository remediation by the agent."""
    repo_name: str
    status: str  # "success", "failure", "skipped"
    pr_urls: List[str] = Field(default_factory=list)
    duration_ms: int = 0
    error: Optional[str] = None
    total_cost_usd: Optional[float] = None
    num_turns: int = 0

class RemediationOrchestratorResult(BaseModel):
    """Aggregated results from remediation orchestrator workflow."""
    status: str  # "success", "partial", "failure"
    org: str
    total_repos: int
    successful_repos: int
    failed_repos: int
    skipped_repos: int
    results: List[AgentRemediationResult] = Field(default_factory=list)
