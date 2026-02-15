"""
Agents package for packagebot.

Contains two main agent orchestrators:
1. dependency-remediation: Updates vulnerable dependencies
2. pull-request: Creates and reviews pull requests

Usage:
    from app.agents import run_full_remediation

    # Run complete workflow
    result = await run_full_remediation(org, repo_data, workspace)

    # Or run individual agents
    from app.agents.dependency_remediation import run_dependency_remediation_agent
    from app.agents.pull_request import run_pull_request_agent
"""

from app.agents.remediation_agent import (
    run_full_remediation,
    run_dependency_remediation_agent,
    run_pull_request_agent,
)

__all__ = [
    "run_full_remediation",
    "run_dependency_remediation_agent",
    "run_pull_request_agent",
]
