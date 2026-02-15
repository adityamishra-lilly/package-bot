"""Jira API exception hierarchy."""


class JiraAPIError(Exception):
    """Base exception for Jira API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class JiraAuthenticationError(JiraAPIError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN."):
        super().__init__(message, status_code=401)


class JiraNotFoundError(JiraAPIError):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found."):
        super().__init__(message, status_code=404)


class JiraPermissionError(JiraAPIError):
    """Raised when the user lacks permissions (403) or read-only mode blocks writes."""

    def __init__(self, message: str = "Permission denied."):
        super().__init__(message, status_code=403)


class JiraValidationError(JiraAPIError):
    """Raised when the request payload is invalid (400)."""

    def __init__(self, message: str = "Validation error."):
        super().__init__(message, status_code=400)
