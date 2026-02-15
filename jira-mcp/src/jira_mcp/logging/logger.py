"""Logging configuration. Outputs to stderr to avoid conflict with stdio MCP transport."""

import logging
import sys


def setup_logger(name: str = "jira_mcp", level: str = "INFO") -> logging.Logger:
    """Create a logger that writes to stderr."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    )
    logger.addHandler(handler)
    return logger
