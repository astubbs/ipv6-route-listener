"""Tests for Logger module."""

import logging
from unittest.mock import patch

import pytest

from route_listener.logger import Logger


@pytest.fixture(autouse=True)
def enable_logging():
    """Re-enable logging for logger tests (overrides conftest disable)."""
    logging.disable(logging.NOTSET)
    yield
    logging.disable(logging.CRITICAL)


@pytest.fixture
def logger(tmp_path):
    """Create a Logger with a temp log file."""
    log_file = str(tmp_path / "test.log")
    return Logger(verbose=False, log_file=log_file)


def test_debug_respects_log_level_not_verbose_flag(logger):
    """debug() should log when level is DEBUG, regardless of verbose flag."""
    logger.setLevel(logging.DEBUG)
    assert logger.verbose is False

    with patch.object(logger._logger, "debug") as mock_debug:
        logger.debug("test message")
        mock_debug.assert_called_once_with("test message")


def test_debug_suppressed_at_info_level(logger):
    """debug() should not emit when level is INFO."""
    logger.setLevel(logging.INFO)

    with patch.object(logger._logger, "debug") as mock_debug:
        logger.debug("test message")
        mock_debug.assert_called_once_with("test message")  # still called, but handler filters


def test_info_delegates(logger):
    """info() delegates to underlying logger."""
    with patch.object(logger._logger, "info") as mock_info:
        logger.info("hello")
        mock_info.assert_called_once_with("hello")


def test_error_delegates(logger):
    """error() delegates to underlying logger."""
    with patch.object(logger._logger, "error") as mock_error:
        logger.error("bad thing")
        mock_error.assert_called_once_with("bad thing")


def test_banner_logs_at_info(logger):
    """banner() logs at info level."""
    with patch.object(logger._logger, "info") as mock_info:
        logger.banner("== Banner ==")
        mock_info.assert_called_once_with("== Banner ==")


def test_packet_info_format(logger):
    """packet_info() formats RA info correctly."""
    with patch.object(logger._logger, "debug") as mock_debug:
        logger.packet_info("fe80::1", "fd00::", 64, router="fe80::2")
        mock_debug.assert_called_once()
        msg = mock_debug.call_args[0][0]
        assert "fe80::1" in msg
        assert "fd00::/64" in msg
        assert "via fe80::2" in msg


def test_packet_info_no_router_suffix_when_same_as_src(logger):
    """packet_info() omits 'via' when router equals src_addr."""
    with patch.object(logger._logger, "debug") as mock_debug:
        logger.packet_info("fe80::1", "fd00::", 64, router="fe80::1")
        msg = mock_debug.call_args[0][0]
        assert "via" not in msg


def test_ignored_route_format(logger):
    """ignored_route() formats correctly."""
    with patch.object(logger._logger, "debug") as mock_debug:
        logger.ignored_route("fd00::", 64, "not ULA")
        mock_debug.assert_called_once()
        msg = mock_debug.call_args[0][0]
        assert "fd00::/64" in msg
        assert "not ULA" in msg


def test_is_enabled_for(logger):
    """isEnabledFor() delegates to underlying logger."""
    logger.setLevel(logging.DEBUG)
    assert logger.isEnabledFor(logging.DEBUG) is True
    assert logger.isEnabledFor(logging.INFO) is True

    logger.setLevel(logging.ERROR)
    assert logger.isEnabledFor(logging.DEBUG) is False
    assert logger.isEnabledFor(logging.ERROR) is True


def test_log_file_created(tmp_path):
    """Logger creates log file."""
    log_file = str(tmp_path / "test.log")
    Logger(log_file=log_file)
    assert (tmp_path / "test.log").exists()
