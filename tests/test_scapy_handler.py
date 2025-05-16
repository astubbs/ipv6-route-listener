"""Tests for the ScapyPacketHandler class."""

import pytest
from unittest.mock import Mock
from route_listener.scapy_handler import ScapyPacketHandler
from route_listener.route_info import RouteInfo

@pytest.fixture
def mock_route_configurator():
    """Create a mock route configurator."""
    configurator = Mock()
    configurator.is_configured.return_value = False
    return configurator

@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock()
    logger.verbose = True
    return logger

@pytest.fixture
def scapy_handler(mock_route_configurator, mock_logger):
    """Create a ScapyPacketHandler instance with mocked dependencies."""
    return ScapyPacketHandler(
        interface="lo0",  # Use loopback interface for testing
        route_configurator=mock_route_configurator,
        logger=mock_logger,
        enable_rs=False
    )

@pytest.fixture
def scapy_handler_disabled_parsing(mock_route_configurator, mock_logger):
    """Create a ScapyPacketHandler instance with packet parsing disabled."""
    return ScapyPacketHandler(
        interface="lo0",  # Use loopback interface for testing
        route_configurator=mock_route_configurator,
        logger=mock_logger,
        enable_rs=False,
        enable_parsing=False
    )

def test_handle_router_advertisement(scapy_handler, mock_route_configurator):
    """Test handling of a Router Advertisement with both prefix and route options."""
    # Create route info objects directly (as if they were parsed from a packet)
    route_infos = [
        RouteInfo(
            prefix="fd82:cd32:5ad7:ff4a::",
            prefix_len=64,
            router="fe80::1",
            is_prefix=True,
            valid_time=1800,
            pref_time=1800
        ),
        RouteInfo(
            prefix="fd2b:7eb9:619c::",
            prefix_len=64,
            router="fe80::1",
            is_prefix=False,
            lifetime=1800
        )
    ]
    
    # Process the route information
    scapy_handler.route_processor.process_route_infos(route_infos)
    
    # Verify that configure was called for both the prefix and route
    assert mock_route_configurator.configure.call_count == 2
    
    # Verify prefix configuration
    mock_route_configurator.configure.assert_any_call(
        "fd82:cd32:5ad7:ff4a::",
        64,
        "fe80::1",
        is_prefix=True
    )
    
    # Verify route configuration
    mock_route_configurator.configure.assert_any_call(
        "fd2b:7eb9:619c::",
        64,
        "fe80::1",
        is_prefix=False
    )

def test_handle_router_advertisement_with_disabled_parsing(scapy_handler_disabled_parsing, mock_route_configurator):
    """Test handling of a Router Advertisement with packet parsing disabled."""
    # Create route info objects directly (as if they were parsed from a packet)
    route_infos = [
        RouteInfo(
            prefix="fd82:cd32:5ad7:ff4a::",
            prefix_len=64,
            router="fe80::1",
            is_prefix=True,
            valid_time=1800,
            pref_time=1800
        ),
        RouteInfo(
            prefix="fd2b:7eb9:619c::",
            prefix_len=64,
            router="fe80::1",
            is_prefix=False,
            lifetime=1800
        )
    ]
    
    # Process the route information with parsing disabled
    scapy_handler_disabled_parsing.route_processor.process_route_infos(route_infos)
    
    # Verify that configure was not called (since parsing is disabled)
    mock_route_configurator.configure.assert_not_called()