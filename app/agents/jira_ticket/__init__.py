"""
Jira Ticket Agent package.

This agent handles Jira ticket creation and review with two subagents:
- creator-agent: Creates Bug issues to track security PR review
- reviewer-agent: Reviews tickets for quality and can self-correct
"""

from .agent import run_jira_ticket_agent, JIRA_ORCHESTRATOR_APPROVED_TOOLS
from .subagents import (
    creator_agent,
    reviewer_agent,
)

__all__ = [
    "run_jira_ticket_agent",
    "JIRA_ORCHESTRATOR_APPROVED_TOOLS",
    "creator_agent",
    "reviewer_agent",
]
