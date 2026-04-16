"""End-to-end tests: real Scapy RA packet -> real PacketParser -> RouteConfigurator.

The unit-level tests in tests/test_router_advertisement.py call
process_packet_info() directly with parsed-info dicts. This file tests the
full chain by feeding actual Scapy-constructed packets through the real
PacketParser, with only the RouteExecutor mocked (so we don't run shell
commands).
"""

import pytest
from scapy.all import (
    Ether,
    ICMPv6ND_RA,
    ICMPv6NDOptPrefixInfo,
    ICMPv6NDOptRouteInfo,
    IPv6,
)

from route_listener.packet_parser import PacketParser
from route_listener.route_configurator import Route


@pytest.fixture
def packet_parser():
    """Real PacketParser - no mocking."""
    return PacketParser()


def _build_ra(*, src: str, prefix: str | None = None, route: str | None = None):
    """Construct a real Scapy Router Advertisement packet."""
    pkt = Ether() / IPv6(src=src, dst="ff02::1") / ICMPv6ND_RA()
    if prefix is not None:
        pkt = pkt / ICMPv6NDOptPrefixInfo(
            prefix=prefix, prefixlen=64, validlifetime=1800, preferredlifetime=1800
        )
    if route is not None:
        pkt = pkt / ICMPv6NDOptRouteInfo(prefix=route, plen=64, rtlifetime=1800)
    return pkt


def test_real_ra_with_ula_prefix_and_route_is_processed_end_to_end(
    packet_parser, route_configurator, mock_executor
):
    """Real Scapy RA packet -> real parser -> configurator -> mocked executor."""
    src_ip = "fe80::f209:dff:fe35:48a"
    prefix_addr = "fd82:cd32:5ad7:ff4a::"
    route_addr = "fd4e:a053:febd::"

    packet = _build_ra(src=src_ip, prefix=prefix_addr, route=route_addr)

    # Real parser - no MagicMock around parse() this time.
    packet_info = packet_parser.parse(packet)
    route_configurator.process_packet_info(packet_info)

    assert mock_executor.execute.call_count == 2
    configured_prefixes = [call[0][0].prefix for call in mock_executor.execute.call_args_list]
    assert prefix_addr in configured_prefixes
    assert route_addr in configured_prefixes

    # Both Routes should carry the source address as the router.
    for call in mock_executor.execute.call_args_list:
        configured_route = call[0][0]
        assert isinstance(configured_route, Route)
        assert configured_route.router == src_ip
        assert configured_route.interface == "eth0"


def test_real_ra_with_non_ula_prefix_is_ignored_end_to_end(
    packet_parser, route_configurator, mock_executor
):
    """Non-ULA prefix in a real packet should not trigger any executor call."""
    packet = _build_ra(src="fe80::f209:dff:fe35:48a", prefix="2406:e001:abcd:5600::")

    packet_info = packet_parser.parse(packet)
    route_configurator.process_packet_info(packet_info)

    mock_executor.execute.assert_not_called()


def test_real_ra_repeated_does_not_reconfigure_end_to_end(
    packet_parser, route_configurator, mock_executor
):
    """Sending the same RA twice through the full pipeline configures each route once."""
    packet = _build_ra(
        src="fe80::f209:dff:fe35:48a",
        prefix="fd82:cd32:5ad7:ff4a::",
        route="fd4e:a053:febd::",
    )

    for _ in range(2):
        packet_info = packet_parser.parse(packet)
        route_configurator.process_packet_info(packet_info)

    # Two routes (prefix + route) configured exactly once each.
    assert mock_executor.execute.call_count == 2


def test_real_ra_executor_failure_does_not_mark_route_seen(
    packet_parser, route_configurator, mock_executor
):
    """If the executor reports failure, the route must remain unseen so a
    subsequent RA gets retried."""
    mock_executor.execute.return_value = False
    packet = _build_ra(
        src="fe80::f209:dff:fe35:48a",
        prefix="fd82:cd32:5ad7:ff4a::",
        route="fd4e:a053:febd::",
    )

    packet_info = packet_parser.parse(packet)
    route_configurator.process_packet_info(packet_info)

    assert len(route_configurator.seen_routes) == 0
