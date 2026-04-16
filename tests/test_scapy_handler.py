"""Tests for ScapyPacketHandler."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from scapy.all import IPv6

from route_listener.logger import Logger
from route_listener.packet_parser import PacketParser
from route_listener.route_configurator import RouteConfigurator
from route_listener.router_solicitor import RouterSolicitor
from route_listener.scapy_handler import ScapyPacketHandler


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = MagicMock(spec=Logger)
    logger.verbose = True
    return logger


@pytest.fixture
def mock_route_configurator():
    """Create a mock route configurator for testing."""
    configurator = MagicMock(spec=RouteConfigurator)
    configurator.process_packet_info = MagicMock()
    return configurator


@pytest.fixture
def mock_packet_parser():
    """Create a mock packet parser for testing."""
    return MagicMock(spec=PacketParser)


@pytest.fixture
def mock_router_solicitor():
    """Create a mock router solicitor for testing."""
    solicitor = MagicMock(spec=RouterSolicitor)
    solicitor.send = MagicMock()
    return solicitor


@pytest.fixture
def scapy_handler(mock_route_configurator, mock_logger):
    """Create a ScapyPacketHandler instance for testing."""
    return ScapyPacketHandler(
        interface="lo0",  # Use loopback interface for testing
        route_configurator=mock_route_configurator,
        logger=mock_logger,
        enable_rs=False,
    )


def test_handle_router_advertisement(scapy_handler, mock_route_configurator, mock_logger):
    """Test handling of a Router Advertisement with both prefix and route options."""
    # Create a dummy packet
    dummy_packet = Mock()

    # Configure the mock parser to return our test data
    scapy_handler.packet_parser.parse = Mock(
        return_value={
            "src_ip": "fe80::1",
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
            "routes": [{"address": "fd2b:7eb9:619c::", "length": 64, "lifetime": 1800}],
        }
    )

    # Process the packet
    scapy_handler._handle_packet(dummy_packet)

    # Verify that process_packet_info was called with the correct data
    mock_route_configurator.process_packet_info.assert_called_once()
    call_args = mock_route_configurator.process_packet_info.call_args[0][0]
    assert call_args["src_ip"] == "fe80::1"
    assert call_args["prefixes"][0]["address"] == "fd82:cd32:5ad7:ff4a::"
    assert call_args["routes"][0]["address"] == "fd2b:7eb9:619c::"


def test_handle_packet_error(scapy_handler, mock_logger):
    """Test error handling in packet processing."""
    # Create a dummy packet
    dummy_packet = Mock()

    # Configure the parser to raise an exception
    scapy_handler.packet_parser.parse = Mock(side_effect=Exception("Test error"))

    # Process the packet
    scapy_handler._handle_packet(dummy_packet)

    # Verify error was logged
    mock_logger.error.assert_called_once()
    assert "Test error" in mock_logger.error.call_args[0][0]


def test_start_with_rs(scapy_handler, mock_logger):
    """Test starting the packet handler with Router Solicitation enabled."""
    # Create a mock router solicitor
    mock_solicitor = MagicMock(spec=RouterSolicitor)
    mock_solicitor.send = MagicMock()
    scapy_handler.router_solicitor = mock_solicitor

    # Mock sniff to avoid actual packet capture
    with patch("route_listener.scapy_handler.sniff") as mock_sniff:
        # Start the handler
        scapy_handler.start()

        # Verify Router Solicitation was sent
        mock_solicitor.send.assert_called_once()

        # Verify sniff was called with correct parameters
        mock_sniff.assert_called_once()
        call_args = mock_sniff.call_args[1]
        assert call_args["iface"] == "lo0"
        assert call_args["filter"] == "icmp6 and ip6[40] = 134"
        assert call_args["store"] == 0


def test_start_without_rs(scapy_handler, mock_logger):
    """Test starting the packet handler without Router Solicitation."""
    # Ensure Router Solicitation is disabled
    scapy_handler.router_solicitor = None

    # Mock sniff to avoid actual packet capture
    with patch("route_listener.scapy_handler.sniff") as mock_sniff:
        # Start the handler
        scapy_handler.start()

        # Verify sniff was called with correct parameters
        mock_sniff.assert_called_once()
        call_args = mock_sniff.call_args[1]
        assert call_args["iface"] == "lo0"
        assert call_args["filter"] == "icmp6 and ip6[40] = 134"
        assert call_args["store"] == 0


def test_ignore_non_ipv6_packet(scapy_handler, mock_logger):
    """Test that non-IPv6 packets are ignored and logged in verbose mode."""
    # Create a non-IPv6 packet
    non_ipv6_packet = Mock()
    non_ipv6_packet.haslayer = Mock(return_value=False)

    # Process the packet
    scapy_handler._handle_packet(non_ipv6_packet)

    # Verify debug logging occurred
    mock_logger.debug.assert_called_with("Ignoring non-IPv6 packet")


def test_ignore_non_ra_packet(scapy_handler, mock_logger):
    """Test that non-RA packets are ignored and logged in verbose mode."""
    # Create an IPv6 packet without RA
    ipv6_packet = Mock()
    ipv6_packet.haslayer = Mock(side_effect=lambda x: x == IPv6)

    # Process the packet
    scapy_handler._handle_packet(ipv6_packet)

    # Verify debug logging occurred
    mock_logger.debug.assert_called_with("Ignoring non-RA packet")


def test_process_valid_ra_packet(scapy_handler, mock_logger, mock_route_configurator):
    """Test that valid RA packets are processed and logged."""
    # Create a valid RA packet
    ra_packet = Mock()
    ra_packet.haslayer = Mock(return_value=True)
    ra_packet.summary = Mock(return_value="RA packet summary")

    # Configure the parser to return test data
    scapy_handler.packet_parser.parse = Mock(
        return_value={
            "src_ip": "fe80::1",
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
        }
    )

    # Process the packet
    scapy_handler._handle_packet(ra_packet)

    # Verify info logging occurred
    mock_logger.info.assert_called_with("✅ Processed Router Advertisement")

    # Verify packet was processed
    mock_route_configurator.process_packet_info.assert_called_once()
