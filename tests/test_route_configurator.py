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
        configurator.process_packet_info({
            "src_ip": "fe80::1",
            "prefix": {"address": "fd00::", "length": 64},
        })

    mock_configure.assert_called_once_with("fd00::", 64, router="fe80::1", is_prefix=True)


def test_process_packet_info_non_ula_prefix_ignored(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator, "configure") as mock_configure:
        configurator.process_packet_info({
            "src_ip": "fe80::1",
            "prefix": {"address": "2001:db8::", "length": 64},
        })

    mock_configure.assert_not_called()


def test_process_packet_info_ula_route(mock_logger):
    configurator = RouteConfigurator(mock_logger, interface="eth0")

    with patch.object(configurator, "configure") as mock_configure:
        configurator.process_packet_info({
            "src_ip": "fe80::1",
            "route": {"address": "fd2b:7eb9:619c::", "length": 48},
        })

    mock_configure.assert_called_once_with(
        "fd2b:7eb9:619c::", 48, router="fe80::1", is_prefix=False
    )
