"""
Agents package for packagebot.

Contains three main agent orchestrators:
1. dependency-remediation: Updates vulnerable dependencies
2. pull-request: Creates and reviews pull requests
3. jira-ticket: Creates and reviews Jira tickets for PR tracking

Usage:
    from app.agents import run_full_remediation

    # Run complete workflow
    result = await run_full_remediation(org, repo_data, workspace)

    # Or run individual agents
    from app.agents.dependency_remediation import run_dependency_remediation_agent
    from app.agents.pull_request import run_pull_request_agent
    from app.agents.jira_ticket import run_jira_ticket_agent
"""

from app.agents.remediation_agent import (
    run_full_remediation,
    run_dependency_remediation_agent,
    run_pull_request_agent,
    run_jira_ticket_agent,
)

__all__ = [
    "run_full_remediation",
    "run_dependency_remediation_agent",
    "run_pull_request_agent",
    "run_jira_ticket_agent",
]
