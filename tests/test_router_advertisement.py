"""Unit tests for Router Advertisement processing in RouteConfigurator.

These exercise process_packet_info() directly with parsed-info dicts.
Real-packet end-to-end tests live in tests/integration/test_route_processing.py.
"""

from route_listener.route_configurator import Route

from .conftest import SAMPLE_RA_PAYLOADS


def test_process_ula_prefix_and_route(route_configurator, mock_executor):
    """ULA prefix + ULA route: both get configured."""
    ra_data = SAMPLE_RA_PAYLOADS[0]

    route_configurator.process_packet_info(ra_data)

    assert mock_executor.execute.call_count == 2
    calls = mock_executor.execute.call_args_list

    prefix_route = calls[0][0][0]
    assert isinstance(prefix_route, Route)
    assert prefix_route.prefix == ra_data["prefix"]["address"]
    assert prefix_route.router == ra_data["src_ip"]
    assert prefix_route.interface == "eth0"
    assert prefix_route.is_prefix

    route_obj = calls[1][0][0]
    assert isinstance(route_obj, Route)
    assert route_obj.prefix == ra_data["route"]["address"]
    assert route_obj.router == ra_data["src_ip"]
    assert route_obj.interface == "eth0"
    assert not route_obj.is_prefix


def test_process_non_ula_prefix(route_configurator, mock_executor):
    """Non-ULA prefix is ignored."""
    route_configurator.process_packet_info(SAMPLE_RA_PAYLOADS[1])

    mock_executor.execute.assert_not_called()


def test_process_ula_prefix_only(route_configurator, mock_executor):
    """ULA prefix without a route: only the prefix is configured."""
    ra_data = SAMPLE_RA_PAYLOADS[2]

    route_configurator.process_packet_info(ra_data)

    mock_executor.execute.assert_called_once()
    route = mock_executor.execute.call_args[0][0]
    assert isinstance(route, Route)
    assert route.prefix == ra_data["prefix"]["address"]
    assert route.is_prefix


def test_duplicate_route_handling(route_configurator, mock_executor):
    """Processing the same payload twice still only configures each route once."""
    ra_data = SAMPLE_RA_PAYLOADS[0]

    route_configurator.process_packet_info(ra_data)
    route_configurator.process_packet_info(ra_data)

    # Two routes total (prefix + route), each from the first call only.
    assert mock_executor.execute.call_count == 2


def test_route_configuration_failure(route_configurator, mock_executor):
    """When the executor reports failure, routes do not get marked as seen."""
    mock_executor.execute.return_value = False

    route_configurator.process_packet_info(SAMPLE_RA_PAYLOADS[0])

    assert len(route_configurator.seen_routes) == 0
