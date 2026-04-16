"""Tests for RouteConfigurator, RouteExecutor, and Route."""

from unittest.mock import MagicMock, patch

import pytest

from route_listener.logger import Logger
from route_listener.route_configurator import Route, RouteConfigurator, RouteExecutor


@pytest.fixture
def mock_logger():
    logger = MagicMock(spec=Logger)
    return logger


# --- Route dataclass tests ---


def test_route_is_ula_true():
    route = Route(prefix="fd00::1", router="fe80::1", interface="eth0")
    assert route.is_ula() is True


def test_route_is_ula_false():
    route = Route(prefix="2001:db8::1", router="fe80::1", interface="eth0")
    assert route.is_ula() is False


def test_route_get_route_key_strips_prefix_length():
    route = Route(prefix="fd00::/64", router="fe80::1", interface="eth0", is_prefix=True)
    key = route.get_route_key()
    assert key == "fd00::|fe80::1|eth0|True"


def test_route_str_prefix():
    route = Route(prefix="fd00::", router="fe80::1", interface="eth0", is_prefix=True)
    assert "prefix" in str(route)


def test_route_str_route():
    route = Route(prefix="fd00::", router="fe80::1", interface="eth0", is_prefix=False)
    assert "route" in str(route)


# --- RouteExecutor tests ---


def test_executor_sets_env_vars(mock_logger):
    executor = RouteExecutor(mock_logger, interface="br0")
    route = Route(prefix="fd00::", router="fe80::1", interface="br0", is_prefix=True)

    with patch("route_listener.route_configurator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = executor.execute(route, prefix_len=64)

    assert result is True
    env = mock_run.call_args[1]["env"]
    assert env["PREFIX"] == "fd00::"
    assert env["PREFIX_LEN"] == "64"
    assert env["IFACE"] == "br0"
    assert env["ROUTER"] == "fe80::1"
    assert env["IS_PREFIX"] == "1"


def test_executor_returns_false_on_nonzero_exit(mock_logger):
    executor = RouteExecutor(mock_logger, interface="eth0")
    route = Route(prefix="fd00::", router="fe80::1", interface="eth0")

    with patch("route_listener.route_configurator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = executor.execute(route, prefix_len=64)

    assert result is False
    mock_logger.error.assert_called()


def test_executor_handles_exception(mock_logger):
    executor = RouteExecutor(mock_logger, interface="eth0")
    route = Route(prefix="fd00::", router="fe80::1", interface="eth0")

    with patch("route_listener.route_configurator.subprocess.run", side_effect=Exception("boom")):
        result = executor.execute(route, prefix_len=64)

    assert result is False
    mock_logger.error.assert_called()


# --- RouteConfigurator tests ---


def test_is_configured_false_initially(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")
    assert configurator.is_configured("fd00::", 64) is False


def test_configure_adds_to_seen_routes(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator.executor, "execute", return_value=True):
        configurator.configure("fd00::", 64, router="fe80::1")

    # Verify the route key was added to seen_routes
    route = Route(prefix="fd00::", router="fe80::1", interface="eth0")
    assert route.get_route_key() in configurator.seen_routes


def test_configure_skips_already_seen(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator.executor, "execute", return_value=True) as mock_exec:
        configurator.configure("fd00::", 64, router="fe80::1")
        configurator.configure("fd00::", 64, router="fe80::1")

    mock_exec.assert_called_once()


def test_configure_does_not_add_on_failure(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator.executor, "execute", return_value=False):
        configurator.configure("fd00::", 64, router="fe80::1")

    assert configurator.is_configured("fd00::", 64) is False


def test_process_packet_info_ula_prefix(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator, "configure") as mock_configure:
        configurator.process_packet_info(
            {
                "src_ip": "fe80::1",
                "prefixes": [{"address": "fd00::", "length": 64}],
                "routes": [],
            }
        )

    mock_configure.assert_called_once_with("fd00::", 64, router="fe80::1", is_prefix=True)


def test_process_packet_info_non_ula_prefix_ignored(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator, "configure") as mock_configure:
        configurator.process_packet_info(
            {
                "src_ip": "fe80::1",
                "prefixes": [{"address": "2001:db8::", "length": 64}],
                "routes": [],
            }
        )

    mock_configure.assert_not_called()


def test_process_packet_info_ula_route(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator, "configure") as mock_configure:
        configurator.process_packet_info(
            {
                "src_ip": "fe80::1",
                "prefixes": [],
                "routes": [{"address": "fd2b:7eb9:619c::", "length": 48}],
            }
        )

    mock_configure.assert_called_once_with(
        "fd2b:7eb9:619c::", 48, router="fe80::1", is_prefix=False
    )


def test_configure_warns_when_router_changes_for_known_prefix(mock_logger):
    """If the same prefix is later advertised by a different router, log it -
    the OS route gets silently replaced, so the operator should know."""
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator.executor, "execute", return_value=True):
        configurator.configure("fd00::", 64, router="fe80::1")
        configurator.configure("fd00::", 64, router="fe80::2")  # different router!

    # Find the warning message about the router change.
    warning_calls = [
        call for call in mock_logger.error.call_args_list if "now advertised by" in call.args[0]
    ]
    assert len(warning_calls) == 1
    msg = warning_calls[0].args[0]
    assert "fe80::2" in msg
    assert "fe80::1" in msg


def test_configure_does_not_warn_for_same_router(mock_logger):
    """No warning when the same prefix re-appears via the same router."""
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator.executor, "execute", return_value=True):
        configurator.configure("fd00::", 64, router="fe80::1")
        # Reset seen_routes so configure() actually runs the second time -
        # we're testing the router-change check, not the dedup path.
        configurator.seen_routes.clear()
        configurator.configure("fd00::", 64, router="fe80::1")

    warning_calls = [
        call for call in mock_logger.error.call_args_list if "now advertised by" in call.args[0]
    ]
    assert warning_calls == []


def test_process_packet_info_multiple_prefixes(mock_logger):
    """Multi-prefix RA: every prefix in the list gets configured."""
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator, "configure") as mock_configure:
        configurator.process_packet_info(
            {
                "src_ip": "fe80::1",
                "prefixes": [
                    {"address": "fd00::", "length": 64},
                    {"address": "fd11::", "length": 64},
                    {"address": "2001:db8::", "length": 64},  # non-ULA, ignored
                ],
                "routes": [
                    {"address": "fd22::", "length": 48},
                    {"address": "fd33::", "length": 48},
                ],
            }
        )

    # 2 ULA prefixes + 2 ULA routes; non-ULA prefix is filtered out.
    assert mock_configure.call_count == 4
    configured = {call.args[0] for call in mock_configure.call_args_list}
    assert configured == {"fd00::", "fd11::", "fd22::", "fd33::"}
