"""Tests for packet filtering and logging behavior."""

import pytest
from unittest.mock import Mock, patch, call, ANY
from scapy.all import IPv6, ICMPv6ND_RA, ICMPv6NDOptPrefixInfo, ICMPv6NDOptRouteInfo
from route_listener.scapy_handler import ScapyPacketHandler
from route_listener.logger import Logger

# Test data constants
TEST_ROUTER = "fe80::1"
TEST_PREFIX = "fd82:cd32:5ad7:ff4a::"
TEST_ROUTE = "fd4e:a053:febd::"
TEST_PREFIX_LEN = 64
TEST_LIFETIME = 1800

@pytest.fixture
def mock_route_configurator():
    """Create a mock route configurator."""
    configurator = Mock()
    configurator.is_configured.return_value = False  # By default, routes are not configured
    return configurator

@pytest.fixture
def mock_logger():
    """Create a mock logger with verbose mode enabled."""
    logger = Mock(spec=Logger)
    logger.verbose = True
    logger.debug = Mock()
    logger.info = Mock()
    logger.error = Mock()
    return logger

@pytest.fixture
def packet_handler(mock_route_configurator, mock_logger):
    """Create a packet handler with mocked dependencies."""
    return ScapyPacketHandler(
        interface="eth0",
        route_configurator=mock_route_configurator,
        logger=mock_logger
    )

def test_ignore_non_ipv6_packet(packet_handler, mock_logger):
    """Test that non-IPv6 packets are ignored and logged in verbose mode."""
    non_ipv6_packet = Mock()
    non_ipv6_packet.__iter__ = Mock(return_value=iter([]))
    packet_handler._handle_packet(non_ipv6_packet)
    # Verify that debug logging occurred
    mock_logger.debug.assert_called()

def test_ignore_non_ra_packet(packet_handler, mock_logger):
    """Test that non-RA packets are ignored and logged in verbose mode."""
    ipv6_packet = IPv6(src=TEST_ROUTER, dst="ff02::1")
    packet_handler._handle_packet(ipv6_packet)
    # Verify that debug logging occurred
    mock_logger.debug.assert_called()

def test_process_valid_ra_packet(packet_handler, mock_logger, mock_route_configurator):
    """Test that valid RA packets are processed and logged."""
    ra_packet = IPv6(src=TEST_ROUTER, dst="ff02::1")/ICMPv6ND_RA()
    prefix_opt = ICMPv6NDOptPrefixInfo(
        prefix=TEST_PREFIX,
        prefixlen=TEST_PREFIX_LEN,
        validlifetime=TEST_LIFETIME,
        preferredlifetime=TEST_LIFETIME
    )
    ra_packet.add_payload(prefix_opt)
    packet_handler._handle_packet(ra_packet)
    # Verify that info logging occurred
    mock_logger.info.assert_called()

def test_ignore_duplicate_ra(packet_handler, mock_logger):
    """Test that duplicate RAs are ignored and logged in verbose mode."""
    ra_packet = IPv6(src=TEST_ROUTER, dst="ff02::1")/ICMPv6ND_RA()
    packet_handler._handle_packet(ra_packet)
    packet_handler._handle_packet(ra_packet)
    assert mock_logger.debug.call_count > 0

def test_log_packet_details_in_verbose_mode(packet_handler, mock_logger):
    """Test that packet details are logged in verbose mode."""
    ra_packet = IPv6(src=TEST_ROUTER, dst="ff02::1")/ICMPv6ND_RA()
    prefix_opt = ICMPv6NDOptPrefixInfo(
        prefix=TEST_PREFIX,
        prefixlen=TEST_PREFIX_LEN,
        validlifetime=TEST_LIFETIME,
        preferredlifetime=TEST_LIFETIME
    )
    route_opt = ICMPv6NDOptRouteInfo(
        prefix=TEST_ROUTE,
        plen=TEST_PREFIX_LEN,
        rtlifetime=TEST_LIFETIME
    )
    ra_packet.add_payload(prefix_opt)
    ra_packet.add_payload(route_opt)
    
    # Process the packet
    packet_handler._handle_packet(ra_packet)
    
    # Verify that logging occurred
    assert mock_logger.debug.call_count > 0 