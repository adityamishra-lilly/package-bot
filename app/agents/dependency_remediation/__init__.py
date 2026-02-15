"""
Dependency Remediation Agent package.

This agent orchestrates dependency vulnerability remediation with three subagents:
- planner-agent: Analyzes vulnerabilities and creates update plan
- executor-agent: Performs sparse checkout and updates
- verifier-agent: Validates updates were successful
"""

from .agent import run_dependency_remediation_agent, ORCHESTRATOR_APPROVED_TOOLS
from .subagents import (
    planner_agent,
    executor_agent,
    verifier_agent,
)

__all__ = [
    "run_dependency_remediation_agent",
    "ORCHESTRATOR_APPROVED_TOOLS",
    "planner_agent",
    "executor_agent",
    "verifier_agent",
]
