"""Tests for packet parsing functionality."""


import pytest
from scapy.all import (
    Ether,
    ICMPv6ND_RA,
    ICMPv6NDOptPrefixInfo,
    ICMPv6NDOptRouteInfo,
    ICMPv6NDOptSrcLLAddr,
    IPv6,
)

from route_listener.packet_parser import PacketParser


@pytest.fixture
def packet_parser():
    """Create a PacketParser instance for testing."""
    return PacketParser()


def test_parse_ra_with_all_options(packet_parser):
    """Test parsing a Router Advertisement packet with prefix info, route info, and source link-layer address."""
    # Create a Router Advertisement packet with all options
    ra_packet = (
        Ether(src="94:ea:32:a1:0f:ac")
        / IPv6(src="fe80::92ea:32ff:fea1:fac", dst="ff02::1")
        / ICMPv6ND_RA()
        / ICMPv6NDOptPrefixInfo(
            prefix="fd82:cd32:5ad7:ff4a::", prefixlen=64, validlifetime=1800, preferredlifetime=1800
        )
        / ICMPv6NDOptRouteInfo(prefix="fd4e:a053:febd::", plen=64, rtlifetime=1800)
        / ICMPv6NDOptSrcLLAddr(lladdr="94:ea:32:a1:0f:ac")
    )

    # Parse the packet
    packet_info = packet_parser.parse(ra_packet)

    # Verify the parsed information
    assert packet_info["src_ip"] == "fe80::92ea:32ff:fea1:fac"

    # Verify prefix information (prefixes is always a list)
    assert len(packet_info["prefixes"]) == 1
    prefix_info = packet_info["prefixes"][0]
    assert prefix_info["address"] == "fd82:cd32:5ad7:ff4a::"
    assert prefix_info["length"] == 64
    assert prefix_info["on_link"] is True
    assert prefix_info["autonomous"] is True
    assert prefix_info["valid_time"] == 1800
    assert prefix_info["pref_time"] == 1800

    # Verify route information (routes is always a list)
    assert len(packet_info["routes"]) == 1
    route_info = packet_info["routes"][0]
    assert route_info["address"] == "fd4e:a053:febd::"
    assert route_info["length"] == 64
    assert route_info["lifetime"] == 1800


def test_parse_ra_with_malformed_options(packet_parser):
    """Test parsing a Router Advertisement packet with malformed options."""
    # Create a Router Advertisement packet with malformed options
    ra_packet = (
        Ether(src="94:ea:32:a1:0f:ac")
        / IPv6(src="fe80::92ea:32ff:fea1:fac", dst="ff02::1")
        / ICMPv6ND_RA()
        / ICMPv6NDOptPrefixInfo(
            prefix="fd82:cd32:5ad7:ff4a::", prefixlen=64, validlifetime=1800, preferredlifetime=1800
        )
        / ICMPv6NDOptRouteInfo(prefix="fd4e:a053:febd::", plen=64, rtlifetime=1800)
        / ICMPv6NDOptSrcLLAddr(lladdr="94:ea:32:a1:0f:ac")
    )

    # Modify the packet to make it malformed
    ra_packet[ICMPv6NDOptPrefixInfo].prefix = None
    ra_packet[ICMPv6NDOptRouteInfo].prefix = None

    # Parse the packet and expect an error
    with pytest.raises(ValueError):
        packet_parser.parse(ra_packet)


def test_parse_ra_with_missing_options(packet_parser):
    """Test parsing a Router Advertisement packet with missing options."""
    # Create a Router Advertisement packet without prefix or route options
    ra_packet = (
        Ether(src="94:ea:32:a1:0f:ac")
        / IPv6(src="fe80::92ea:32ff:fea1:fac", dst="ff02::1")
        / ICMPv6ND_RA()
        / ICMPv6NDOptSrcLLAddr(lladdr="94:ea:32:a1:0f:ac")
    )

    # Parse the packet
    packet_info = packet_parser.parse(ra_packet)

    # Source IP present, prefixes/routes are empty lists.
    assert packet_info["src_ip"] == "fe80::92ea:32ff:fea1:fac"
    assert packet_info["prefixes"] == []
    assert packet_info["routes"] == []
