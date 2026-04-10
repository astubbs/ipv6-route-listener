"""Integration tests for route advertisement processing."""

from unittest.mock import MagicMock

import pytest

from route_listener.logger import Logger
from route_listener.packet_parser import PacketParser
from route_listener.route_configurator import Route, RouteConfigurator, RouteExecutor

# Sample data representing Router Advertisement packets
SAMPLE_RA_PACKETS = [
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

@pytest.fixture
def packet_parser():
    """Create a packet parser instance."""
    return PacketParser()

def test_process_ra_with_prefix_and_route(packet_parser, route_configurator, mock_logger, mock_executor):
    """Test processing of a Router Advertisement with both prefix and route options."""
    # Get test data
    ra_data = SAMPLE_RA_PACKETS[0]
    
    # Create a dummy packet (in real code, this would be a Scapy packet)
    dummy_packet = MagicMock()
    
    # Configure the parser to return our test data
    packet_parser.parse = MagicMock(return_value={
        "src_ip": ra_data["src_ip"],
        "prefix": ra_data["prefix"],
        "route": ra_data["route"]
    })
    
    # Process the packet
    packet_info = packet_parser.parse(dummy_packet)
    
    # Verify the packet was parsed correctly
    assert packet_info["src_ip"] == ra_data["src_ip"]
    assert packet_info["prefix"]["address"] == ra_data["prefix"]["address"]
    assert packet_info["route"]["address"] == ra_data["route"]["address"]
    
    # Process the packet info
    route_configurator.process_packet_info(packet_info)
    
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

    # Verify logging
    mock_logger.info.assert_any_call(f"🔧 Configuring prefix for {ra_data['prefix']['address']}/{ra_data['prefix']['length']}")
    mock_logger.info.assert_any_call(f"🔧 Configuring route for {ra_data['route']['address']}/{ra_data['route']['length']}")

def test_process_ra_with_non_ula_prefix(packet_parser, route_configurator, mock_logger, mock_executor):
    """Test processing of a Router Advertisement with non-ULA prefix."""
    # Get test data
    ra_data = SAMPLE_RA_PACKETS[1]
    
    # Create a dummy packet
    dummy_packet = MagicMock()
    
    # Configure the parser to return our test data
    packet_parser.parse = MagicMock(return_value={
        "src_ip": ra_data["src_ip"],
        "prefix": ra_data["prefix"]
    })
    
    # Process the packet
    packet_info = packet_parser.parse(dummy_packet)
    
    # Verify the packet was parsed correctly
    assert packet_info["src_ip"] == ra_data["src_ip"]
    assert packet_info["prefix"]["address"] == ra_data["prefix"]["address"]
    
    # Process the packet info
    route_configurator.process_packet_info(packet_info)
    
    # Verify no routes were configured (non-ULA prefix should be ignored)
    mock_executor.execute.assert_not_called()

def test_duplicate_route_handling(packet_parser, route_configurator, mock_logger, mock_executor):
    """Test that duplicate routes are not processed multiple times."""
    # Get test data
    ra_data = SAMPLE_RA_PACKETS[0]
    
    # Create a dummy packet
    dummy_packet = MagicMock()
    
    # Configure the parser to return our test data
    packet_parser.parse = MagicMock(return_value={
        "src_ip": ra_data["src_ip"],
        "prefix": ra_data["prefix"],
        "route": ra_data["route"]
    })
    
    # Process the packet twice
    packet_info = packet_parser.parse(dummy_packet)
    route_configurator.process_packet_info(packet_info)
    route_configurator.process_packet_info(packet_info)
    
    # Verify the executor was only called once for each route
    assert mock_executor.execute.call_count == 2
    mock_logger.info.assert_any_call("⏭️  Prefix already configured: fd82:cd32:5ad7:ff4a::/64")
    mock_logger.info.assert_any_call("⏭️  Route already configured: fd4e:a053:febd::/64")

def test_route_configuration_failure(packet_parser, route_configurator, mock_logger, mock_executor):
    """Test handling of route configuration failures."""
    # Configure mock to simulate failure
    mock_executor.execute.return_value = False
    
    # Get test data
    ra_data = SAMPLE_RA_PACKETS[0]
    
    # Create a dummy packet
    dummy_packet = MagicMock()
    
    # Configure the parser to return our test data
    packet_parser.parse = MagicMock(return_value={
        "src_ip": ra_data["src_ip"],
        "prefix": ra_data["prefix"],
        "route": ra_data["route"]
    })
    
    # Process the packet
    packet_info = packet_parser.parse(dummy_packet)
    route_configurator.process_packet_info(packet_info)
    
    # Verify the routes were not added to seen_routes
    assert len(route_configurator.seen_routes) == 0 