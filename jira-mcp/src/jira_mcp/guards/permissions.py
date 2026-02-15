"""Permission sets defining read-only vs write tool groups."""

READ_TOOLS = frozenset({
    "get_issue",
    "get_issue_by_key",
    "search_issues",
    "get_comments",
    "get_transitions",
    "list_projects",
    "get_project",
})

WRITE_TOOLS = frozenset({
    "create_issue",
    "update_issue",
    "assign_issue",
    "delete_issue",
    "add_comment",
    "transition_issue",
})

ALL_TOOLS = READ_TOOLS | WRITE_TOOLS
