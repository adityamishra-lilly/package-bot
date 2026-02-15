"""Shared pytest configuration."""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks integration tests")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly requested."""
    if not config.getoption("-m", default=None) or "integration" not in config.getoption("-m", default=""):
        skip_integration = pytest.mark.skip(reason="use -m integration to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
