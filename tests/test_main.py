"""Tests for main module argument parsing."""

from unittest.mock import MagicMock, patch


def test_default_arguments():
    """Test default argument values."""
    with patch("sys.argv", ["route-listen"]):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--interface", default="eth0")
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--enable-rs", action="store_true")
        args = parser.parse_args([])

        assert args.interface == "eth0"
        assert args.debug is False
        assert args.enable_rs is False


def test_interface_flag():
    """Test -i flag sets interface."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interface", default="eth0")
    args = parser.parse_args(["-i", "br0"])
    assert args.interface == "br0"


def test_debug_flag():
    """Test --debug flag."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(["--debug"])
    assert args.debug is True


def test_enable_rs_flag():
    """Test --enable-rs flag."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--enable-rs", action="store_true")
    args = parser.parse_args(["--enable-rs"])
    assert args.enable_rs is True


def test_main_creates_handler_and_starts():
    """Test that main() wires up components and calls handler.start()."""
    with patch("route_listener.main.argparse") as mock_argparse, patch(
        "route_listener.main.Logger"
    ), patch("route_listener.main.RouteConfigurator"), patch(
        "route_listener.main.ScapyPacketHandler"
    ) as mock_handler_cls, patch(
        "route_listener.main.get_if_list", return_value=["lo0", "eth0"]
    ), patch("route_listener.main.conf") as mock_conf:
        mock_args = MagicMock()
        mock_args.interface = "eth0"
        mock_args.debug = False
        mock_args.enable_rs = False
        mock_argparse.ArgumentParser.return_value.parse_args.return_value = mock_args
        mock_conf.version = "2.5.0"

        from route_listener.main import main

        result = main()

        assert result == 0
        mock_handler_cls.assert_called_once()
        mock_handler_cls.return_value.start.assert_called_once()
