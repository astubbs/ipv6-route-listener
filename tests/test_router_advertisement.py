"""Tests for Router Advertisement processing."""

from unittest.mock import MagicMock

import pytest

from route_listener.logger import Logger
from route_listener.route_configurator import Route, RouteConfigurator, RouteExecutor

# Sample Router Advertisement data
TEST_RAS = [
    {
        "description": "RA with ULA prefix and route",
        "src_ip": "fe80::f209:dff:fe35:48a",
        "prefix": {
            "address": "fd82:cd32:5ad7:ff4a::",
            "length": 64,
            "on_link": True,
            "autonomous": True,
            "valid_time": 1800,
            "pref_time": 1800
        },
        "route": {
            "address": "fd4e:a053:febd::",
            "length": 64,
            "lifetime": 1800
        }
    },
    {
        "description": "RA with non-ULA prefix",
        "src_ip": "fe80::f209:dff:fe35:48a",
        "prefix": {
            "address": "2406:e001:abcd:5600::",
            "length": 64,
            "on_link": True,
            "autonomous": False,
            "valid_time": 86400,
            "pref_time": 14400
        }
    },
    {
        "description": "RA with ULA prefix only",
        "src_ip": "fe80::f209:dff:fe35:48a",
        "prefix": {
            "address": "fd82:cd32:5ad7:ff4a::",
            "length": 64,
            "on_link": True,
            "autonomous": True,
            "valid_time": 1800,
            "pref_time": 1800
        }
    }
]

@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = MagicMock(spec=Logger)
    logger.verbose = True
    return logger

@pytest.fixture
def mock_executor(mock_logger):
    """Create a mock route executor."""
    executor = MagicMock(spec=RouteExecutor)
    executor.execute.return_value = True
    return executor

@pytest.fixture
def route_configurator(mock_logger, mock_executor):
    """Create a RouteConfigurator instance with mocked dependencies."""
    configurator = RouteConfigurator(logger=mock_logger, interface="eth0")
    configurator.executor = mock_executor
    return configurator

def test_process_ula_prefix_and_route(route_configurator, mock_executor):
    """Test processing of a Router Advertisement with ULA prefix and route."""
    # Get test data
    ra_data = TEST_RAS[0]
    
    # Process the packet info
    route_configurator.process_packet_info(ra_data)
    
    # Verify both routes were configured
    assert mock_executor.execute.call_count == 2
    calls = mock_executor.execute.call_args_list

    # Verify prefix route
    prefix_route = calls[0][0][0]
    assert isinstance(prefix_route, Route)
    assert prefix_route.prefix == ra_data["prefix"]["address"]
    assert prefix_route.router == ra_data["src_ip"]
    assert prefix_route.interface == "eth0"
    assert prefix_route.is_prefix

    # Verify off-link route
    route_obj = calls[1][0][0]
    assert isinstance(route_obj, Route)
    assert route_obj.prefix == ra_data["route"]["address"]
    assert route_obj.router == ra_data["src_ip"]
    assert route_obj.interface == "eth0"
    assert not route_obj.is_prefix

def test_process_non_ula_prefix(route_configurator, mock_executor):
    """Test processing of a Router Advertisement with non-ULA prefix."""
    # Get test data
    ra_data = TEST_RAS[1]
    
    # Process the packet info
    route_configurator.process_packet_info(ra_data)
    
    # Verify no routes were configured (non-ULA prefix should be ignored)
    mock_executor.execute.assert_not_called()

def test_process_ula_prefix_only(route_configurator, mock_executor):
    """Test processing of a Router Advertisement with only ULA prefix."""
    # Get test data
    ra_data = TEST_RAS[2]
    
    # Process the packet info
    route_configurator.process_packet_info(ra_data)
    
    # Verify only the prefix route was configured
    mock_executor.execute.assert_called_once()
    route = mock_executor.execute.call_args[0][0]
    assert isinstance(route, Route)
    assert route.prefix == ra_data["prefix"]["address"]
    assert route.router == ra_data["src_ip"]
    assert route.interface == "eth0"
    assert route.is_prefix

def test_duplicate_route_handling(route_configurator, mock_executor):
    """Test that duplicate routes are not processed multiple times."""
    # Get test data
    ra_data = TEST_RAS[0]
    
    # Process the packet info twice
    route_configurator.process_packet_info(ra_data)
    route_configurator.process_packet_info(ra_data)
    
    # Verify the executor was only called once for each route
    assert mock_executor.execute.call_count == 2

def test_route_configuration_failure(route_configurator, mock_executor):
    """Test handling of route configuration failures."""
    # Configure mock to simulate failure
    mock_executor.execute.return_value = False
    
    # Get test data
    ra_data = TEST_RAS[0]
    
    # Process the packet info
    route_configurator.process_packet_info(ra_data)
    
    # Verify the routes were not added to seen_routes
    assert len(route_configurator.seen_routes) == 0 