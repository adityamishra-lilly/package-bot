## Desired Architecture:
ScheduledWorkflow (Entry Point - Cron Triggered)
    └── PackagebotWorkflow(Parent/Dynamic Workflow)
            ├── DependabotAlertsWorkflow(Child - runs first)
            └── AgentExecutorWorkflow(Child - N instances/one for each repository, fire-and-forget)

In this architecture, the ScheduledWorkflow serves as the entry point and is triggered by a cron schedule. It initiates the PackagebotWorkflow, which acts as the parent or dynamic workflow. The PackagebotWorkflow first executes the DependabotAlertsWorkflow, which is responsible for fetching and processing security alerts from GitHub. Once the alerts are processed, the PackagebotWorkflow then spawns multiple instances of the AgentExecutorWorkflow, one for each repository that has alerts. These AgentExecutorWorkflow instances run in a fire-and-forget manner, allowing them to execute independently without blocking the main workflow. This design ensures that the system can efficiently handle multiple repositories and their associated alerts concurrently.


## PackagebotWorkflow (Parent/Dynamic Workflow)
    Should create a child workflow after the DependabotAlertsWorkflow is executed successfully, for each repository that has alerts, the child workflow will be responsible for executing the agent logic for that specific repository. The child workflows will be fire-and-forget, meaning that the parent workflow will not wait for them to complete before moving on to the next one. This allows for concurrent execution of the agent logic across multiple repositories, improving efficiency and reducing overall processing time. The parent workflow can also handle any necessary coordination or aggregation of results from the child workflows if needed.
### Format of the object that should be passed from the PackagebotWorkflow to the AgentExecutorWorkflow (Child Workflow - Fire-and-Forget) should be as follows:
{
  "org": "AgentPOC-Org",
  "source": "github_dependabot_org_alerts",
  "state": "open",
  "repository":
    {
      "name": "golang-test",
      "html_url": "https://github.com/AgentPOC-Org/golang-test",
      "security_alerts": [
        {
          "ecosystem": "go",
          "package": "golang.org/x/crypto",
          "manifests": [
            {
              "path": "go.mod",
              "scope": "runtime"
            }
          ],
          "current_version": null,
          "target_version": "0.45.0",
          "fix_versions": [
            "0.45.0"
          ],
          "severity": "medium",
          "highest_cvss": 5.3,
          "ghsas": [
            "GHSA-f6x5-jh6r-wrfv",
            "GHSA-j5w8-q4qc-rx2x"
          ],
          "cves": [
            "CVE-2025-47914",
            "CVE-2025-58181"
          ],
          "vulnerable_ranges": [
            "< 0.45.0"
          ],
          "summary": "golang.org/x/crypto/ssh/agent vulnerable to panic if message is malformed due to out of bounds read",
          "references": [
            "https://github.com/advisories/GHSA-f6x5-jh6r-wrfv",
            "https://github.com/advisories/GHSA-j5w8-q4qc-rx2x",
            "https://go.dev/cl/721960",
            "https://go.dev/cl/721961",
            "https://go.dev/issue/76363"
          ],
          "alerts": [
            {
              "number": 6,
              "html_url": "https://github.com/AgentPOC-Org/golang-test/security/dependabot/6",
              "summary": "golang.org/x/crypto/ssh/agent vulnerable to panic if message is malformed due to out of bounds read",
              "ghsas": [
                "GHSA-f6x5-jh6r-wrfv"
              ],
              "cves": [
                "CVE-2025-47914"
              ],
              "severity": "medium",
              "vulnerable_version_range": "< 0.45.0"
            },
            {
              "number": 5,
              "html_url": "https://github.com/AgentPOC-Org/golang-test/security/dependabot/5",
              "summary": "golang.org/x/crypto/ssh allows an attacker to cause unbounded memory consumption",
              "ghsas": [
                "GHSA-j5w8-q4qc-rx2x"
              ],
              "cves": [
                "CVE-2025-58181"
              ],
              "severity": "medium",
              "vulnerable_version_range": "< 0.45.0"
            }
          ]
        },
        {
          "ecosystem": "go",
          "package": "github.com/containerd/containerd",
          "manifests": [
            {
              "path": "go.mod",
              "scope": "runtime"
            }
          ],
          "current_version": null,
          "target_version": "2.2.0",
          "fix_versions": [
            "1.6.38",
            "1.7.27",
            "1.7.29",
            "2.0.4",
            "2.0.7",
            "2.1.5",
            "2.2.0"
          ],
          "severity": "high",
          "highest_cvss": 7.3,
          "ghsas": [
            "GHSA-265r-hfxg-fhmg",
            "GHSA-m6hq-p25p-ffr2",
            "GHSA-pwhc-rpq9-4c8w"
          ],
          "cves": [
            "CVE-2024-25621",
            "CVE-2024-40635",
            "CVE-2025-64329"
          ],
          "vulnerable_ranges": [
            "< 1.6.38",
            "< 1.7.29",
            "< 2.0.4",
            "< 2.0.7",
            ">= 1.7.0-beta.0, < 1.7.27",
            ">= 2.1.0-beta.0, < 2.1.5",
            ">= 2.2.0-beta.0, < 2.2.0"
          ],
          "summary": "containerd CRI server: Host memory exhaustion through Attach goroutine leak",
          "references": [
            "https://github.com/advisories/GHSA-265r-hfxg-fhmg",
            "https://github.com/advisories/GHSA-m6hq-p25p-ffr2",
            "https://github.com/advisories/GHSA-pwhc-rpq9-4c8w",
            "https://github.com/containerd/containerd/blob/main/docs/rootless.md",
            "https://github.com/containerd/containerd/commit/05044ec0a9a75232cad458027ca83437aae3f4da"
          ],
          "alerts": [
            {
              "number": 4,
              "html_url": "https://github.com/AgentPOC-Org/golang-test/security/dependabot/4",
              "summary": "containerd CRI server: Host memory exhaustion through Attach goroutine leak",
              "ghsas": [
                "GHSA-m6hq-p25p-ffr2"
              ],
              "cves": [
                "CVE-2025-64329"
              ],
              "severity": "medium",
              "vulnerable_version_range": "< 1.7.29"
            },
            {
              "number": 3,
              "html_url": "https://github.com/AgentPOC-Org/golang-test/security/dependabot/3",
              "summary": "containerd affected by a local privilege escalation via wide permissions on CRI directory",
              "ghsas": [
                "GHSA-pwhc-rpq9-4c8w"
              ],
              "cves": [
                "CVE-2024-25621"
              ],
              "severity": "high",
              "vulnerable_version_range": "< 1.7.29"
            },
            {
              "number": 1,
              "html_url": "https://github.com/AgentPOC-Org/golang-test/security/dependabot/1",
              "summary": "containerd has an integer overflow in User ID handling",
              "ghsas": [
                "GHSA-265r-hfxg-fhmg"
              ],
              "cves": [
                "CVE-2024-40635"
              ],
              "severity": "medium",
              "vulnerable_version_range": ">= 1.7.0-beta.0, < 1.7.27"
            }
          ]
        },
        {
          "ecosystem": "go",
          "package": "github.com/docker/docker",
          "manifests": [
            {
              "path": "go.mod",
              "scope": "runtime"
            }
          ],
          "current_version": null,
          "target_version": "28.0.0",
          "fix_versions": [
            "28.0.0"
          ],
          "severity": "low",
          "highest_cvss": 3.3,
          "ghsas": [
            "GHSA-4vq8-7jfc-9cvp"
          ],
          "cves": [
            "CVE-2025-54410"
          ],
          "vulnerable_ranges": [
            "<= 25.0.12",
            ">= 26.0.0-rc1, < 28.0.0"
          ],
          "summary": "Moby firewalld reload removes bridge network isolation",
          "references": [
            "https://firewalld.org/documentation/howto/reload-firewalld.html",
            "https://github.com/advisories/GHSA-4vq8-7jfc-9cvp",
            "https://github.com/moby/moby/pull/49443",
            "https://github.com/moby/moby/pull/49728",
            "https://github.com/moby/moby/security/advisories/GHSA-4vq8-7jfc-9cvp"
          ],
          "alerts": [
            {
              "number": 2,
              "html_url": "https://github.com/AgentPOC-Org/golang-test/security/dependabot/2",
              "summary": "Moby firewalld reload removes bridge network isolation",
              "ghsas": [
                "GHSA-4vq8-7jfc-9cvp"
              ],
              "cves": [
                "CVE-2025-54410"
              ],
              "severity": "low",
              "vulnerable_version_range": ">= 26.0.0-rc1, < 28.0.0"
            }
          ]
        }
      ]
    }
}

## AgentExecutorWorkflow (Child Workflow - Fire-and-Forget)
    ├── execute_agent_activity (Activity - Executes the agent logic for a specific repository addressing all the alerts for that repository)

  workflow-id:  should be repository name
### execute_agent_activity: 
  use existing activities as example and template to implement the execute_agent_activity, the agent logic should implement the current main.py logic for executing the agent, but it should be refactored to fit into an activity. The activity should take in the necessary parameters such as repository name, list of alerts, and any other relevant information needed to execute the agent logic effectively. The activity will then process the alerts for the given repository and perform the required actions based on the agent's functionality.
  Update the SKILL.md file accordingly should be minimum changes (only update reading the vulnerability-object.json/ this should be changed to reading the object that is being passed to the activity, which should be the list of alerts for the repository)

Use workflow-example.md and worker-example.md as references for how to implement the workflows and worker.

