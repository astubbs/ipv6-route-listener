"""Shared test configurations and fixtures."""

import logging

import pytest

from route_listener.logger import Logger


@pytest.fixture(scope="session")
def test_logger():
    """Create a test logger instance."""
    logger = Logger()
    logger.setLevel(logging.DEBUG)
    return logger

@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging for all tests by default."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET) 