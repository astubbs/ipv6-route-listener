"""Shared test configurations and fixtures."""

import logging
from unittest.mock import MagicMock

import pytest

from route_listener.logger import Logger
from route_listener.route_configurator import RouteConfigurator, RouteExecutor

# Sample Router Advertisement payloads in the shape produced by PacketParser
# (prefixes/routes are lists, since a single RA can carry multiple of each).
# Shared across unit and integration tests.
SAMPLE_RA_PAYLOADS = [
    {
        "description": "RA with ULA prefix and route",
        "src_ip": "fe80::f209:dff:fe35:48a",
        "prefixes": [
            {
                "address": "fd82:cd32:5ad7:ff4a::",
                "length": 64,
                "on_link": True,
                "autonomous": True,
                "valid_time": 1800,
                "pref_time": 1800,
            }
        ],
        "routes": [
            {"address": "fd4e:a053:febd::", "length": 64, "lifetime": 1800},
        ],
    },
    {
        "description": "RA with non-ULA prefix",
        "src_ip": "fe80::f209:dff:fe35:48a",
        "prefixes": [
            {
                "address": "2406:e001:abcd:5600::",
                "length": 64,
                "on_link": True,
                "autonomous": False,
                "valid_time": 86400,
                "pref_time": 14400,
            }
        ],
        "routes": [],
    },
    {
        "description": "RA with ULA prefix only",
        "src_ip": "fe80::f209:dff:fe35:48a",
        "prefixes": [
            {
                "address": "fd82:cd32:5ad7:ff4a::",
                "length": 64,
                "on_link": True,
                "autonomous": True,
                "valid_time": 1800,
                "pref_time": 1800,
            }
        ],
        "routes": [],
    },
]


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


@pytest.fixture
def mock_logger():
    """Mock Logger - shared between unit and integration test files."""
    logger = MagicMock(spec=Logger)
    logger.verbose = True
    return logger


@pytest.fixture
def mock_executor():
    """Mock RouteExecutor that succeeds by default. Tests that need failure
    behavior can override execute.return_value."""
    executor = MagicMock(spec=RouteExecutor)
    executor.execute.return_value = True
    return executor


@pytest.fixture
def route_configurator(mock_logger, mock_executor):
    """RouteConfigurator wired to the mock_logger + mock_executor fixtures."""
    configurator = RouteConfigurator(logger=mock_logger, interface="eth0")
    configurator.executor = mock_executor
    return configurator
