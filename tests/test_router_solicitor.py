"""Tests for RouterSolicitor."""

from unittest.mock import MagicMock, patch

import pytest

from route_listener.logger import Logger
from route_listener.router_solicitor import RouterSolicitor


@pytest.fixture
def mock_logger():
    return MagicMock(spec=Logger)


def test_send_creates_and_sends_rs(mock_logger):
    """Test that send() creates an RS packet and calls sendp."""
    solicitor = RouterSolicitor("eth0", mock_logger)

    with patch("route_listener.router_solicitor.sendp") as mock_sendp:
        solicitor.send()

    mock_sendp.assert_called_once()
    call_args = mock_sendp.call_args
    assert call_args[1]["iface"] == "eth0"
    assert call_args[1]["verbose"] == 0


def test_send_logs_success(mock_logger):
    """Test that send() logs on success."""
    solicitor = RouterSolicitor("eth0", mock_logger)

    with patch("route_listener.router_solicitor.sendp"):
        solicitor.send()

    mock_logger.info.assert_called()


def test_send_handles_error(mock_logger):
    """Test that send() catches and logs exceptions."""
    solicitor = RouterSolicitor("eth0", mock_logger)

    with patch("route_listener.router_solicitor.sendp", side_effect=Exception("no iface")):
        solicitor.send()  # should not raise

    mock_logger.error.assert_called()


def test_send_without_logger():
    """Test that send() works when logger is None."""
    solicitor = RouterSolicitor("eth0", logger=None)

    with patch("route_listener.router_solicitor.sendp"):
        solicitor.send()  # should not raise
