"""Integration tests for route advertisement processing."""

import pytest
from route_listener.route_configurator import RouteConfigurator
from route_listener.logger import Logger
from unittest.mock import patch, MagicMock
import subprocess

# Sample data from rdisc6 output
SAMPLE_RA_DATA = [
    {
        "prefix": "2406:e001:abcd:5600::/64",
        "router": "fe80::f209:dff:fe35:48a",
        "autonomous": False,
        "on_link": True,
        "valid_time": 86400,
        "pref_time": 14400
    },
    {
        "prefix": "fd82:cd32:5ad7:ff4a::/64",
        "router": "fe80::1451:3cb7:4e5f:e588",
        "autonomous": True,
        "on_link": True,
        "valid_time": 1800,
        "pref_time": 1800,
        "route": {
            "prefix": "fd4e:a053:febd::/64",
            "lifetime": 1800
        }
    }
]

@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = MagicMock(spec=Logger)
    logger.verbose = True
    return logger

@pytest.fixture
def route_configurator(mock_logger):
    """Create a RouteConfigurator instance with mocked dependencies."""
    return RouteConfigurator(logger=mock_logger, interface="eth0")

def test_route_processing(route_configurator, mock_logger):
    """Test that routes are correctly processed from router advertisements."""
    with patch('subprocess.run') as mock_run:
        # Configure mock to return success
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Route added successfully\n",
            stderr=""
        )

        # Process each route from the sample data
        for ra in SAMPLE_RA_DATA:
            prefix = ra["prefix"].split('/')[0]
            prefix_len = int(ra["prefix"].split('/')[1])
            router = ra["router"]

            # Configure the route
            route_configurator.configure(prefix, prefix_len, router)

            # Verify the correct command was executed
            mock_run.assert_called()
            call_args = mock_run.call_args[1]
            
            # Verify environment variables
            env = call_args['env']
            assert env['PREFIX'] == prefix
            assert env['PREFIX_LEN'] == str(prefix_len)
            assert env['IFACE'] == 'eth0'
            assert env['ROUTER'] == router

            # Verify the script path
            assert 'configure-ipv6-route.sh' in str(mock_run.call_args.args[0])

            # Verify logging
            mock_logger.info.assert_any_call(f"🔧 Configuring route for {prefix}/{prefix_len}")
            mock_logger.info.assert_any_call("✅ Route configured successfully: Route added successfully\n")

def test_prefix_length_handling(route_configurator, mock_logger):
    """Test that prefix lengths are correctly handled in route configuration."""
    with patch('subprocess.run') as mock_run:
        # Configure mock to return success
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Route added successfully\n",
            stderr=""
        )

        # Test cases with different prefix lengths
        test_cases = [
            ("fd82:cd32:5ad7:ff4a::", 64, "fe80::1451:3cb7:4e5f:e588"),
            ("fd4e:a053:febd::", 48, "fe80::1451:3cb7:4e5f:e588"),
            ("2001:db8::", 32, "fe80::1451:3cb7:4e5f:e588"),
        ]

        for prefix, prefix_len, router in test_cases:
            # Configure the route
            route_configurator.configure(prefix, prefix_len, router)

            # Verify the correct command was executed
            mock_run.assert_called()
            call_args = mock_run.call_args[1]
            
            # Verify environment variables
            env = call_args['env']
            assert env['PREFIX'] == prefix
            assert env['PREFIX_LEN'] == str(prefix_len), f"Expected prefix length {prefix_len}, got {env['PREFIX_LEN']}"
            assert env['IFACE'] == 'eth0'
            assert env['ROUTER'] == router

            # Verify logging includes the correct prefix length
            mock_logger.info.assert_any_call(f"🔧 Configuring route for {prefix}/{prefix_len}")

            # Reset mock for next iteration
            mock_run.reset_mock()

def test_duplicate_route_handling(route_configurator, mock_logger):
    """Test that duplicate routes are not processed multiple times."""
    with patch('subprocess.run') as mock_run:
        # Configure mock to return success
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Route added successfully\n",
            stderr=""
        )

        # Process the same route twice
        prefix = "fd82:cd32:5ad7:ff4a::"
        prefix_len = 64
        router = "fe80::1451:3cb7:4e5f:e588"

        # First configuration
        route_configurator.configure(prefix, prefix_len, router)
        assert mock_run.call_count == 1

        # Second configuration of the same route
        route_configurator.configure(prefix, prefix_len, router)
        
        # Verify the command was only called once
        assert mock_run.call_count == 1
        mock_logger.info.assert_any_call("⏭️  Route already configured: fd82:cd32:5ad7:ff4a::/64")

def test_route_configuration_failure(route_configurator, mock_logger):
    """Test handling of route configuration failures."""
    with patch('subprocess.run') as mock_run:
        # Configure mock to simulate failure
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 
            "configure-ipv6-route.sh",
            stderr="Failed to add route: Invalid prefix"
        )

        # Attempt to configure a route
        prefix = "fd82:cd32:5ad7:ff4a::"
        prefix_len = 64
        router = "fe80::1451:3cb7:4e5f:e588"

        route_configurator.configure(prefix, prefix_len, router)

        # Verify error was logged
        mock_logger.error.assert_called_with("❌ Failed to configure route: Failed to add route: Invalid prefix")

def test_off_link_route_configuration(route_configurator, mock_logger):
    """Test configuration of off-link routes with error handling."""
    with patch('subprocess.run') as mock_run:
        # Configure mock to simulate failure
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 
            "configure-ipv6-route.sh",
            stderr="RTNETLINK answers: File exists",
            output=""
        )

        # Attempt to configure an off-link route
        prefix = "fd2b:7eb9:619c::"
        prefix_len = 64
        router = "fe80::85e:1f44:c26f:229"

        # Configure the route
        route_configurator.configure(prefix, prefix_len, router, is_prefix=False)

        # Verify error was logged
        mock_logger.error.assert_called_with("❌ Failed to configure route: RTNETLINK answers: File exists")
        if mock_logger.verbose:
            mock_logger.debug.assert_any_call("Command output: ")
            mock_logger.debug.assert_any_call("Command error: RTNETLINK answers: File exists")
            mock_logger.debug.assert_any_call("Return code: 1")

def test_off_link_route_processing(route_configurator, mock_logger):
    """Test that off-link routes are processed correctly."""
    with patch('subprocess.run') as mock_run:
        # Configure mock to return success
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Route added successfully\n",
            stderr=""
        )

        # Test data with both on-link prefix and off-link route
        prefix = "fd82:cd32:5ad7:ff4a::"
        prefix_len = 64
        router = "fe80::85e:1f44:c26f:229"
        off_link_route = "fd2b:7eb9:619c::"

        # Configure both the on-link prefix and off-link route
        route_configurator.configure(prefix, prefix_len, router, is_prefix=True)
        route_configurator.configure(off_link_route, prefix_len, router, is_prefix=False)

        # Verify both routes were configured
        assert mock_run.call_count == 2

        # Get all calls
        calls = mock_run.call_args_list

        # Verify on-link prefix configuration
        prefix_call = calls[0]
        prefix_env = prefix_call[1]['env']
        assert prefix_env['PREFIX'] == prefix
        assert prefix_env['PREFIX_LEN'] == str(prefix_len)
        assert prefix_env['IFACE'] == 'eth0'
        assert prefix_env['ROUTER'] == router
        assert prefix_env['IS_PREFIX'] == "1"

        # Verify off-link route configuration
        route_call = calls[1]
        route_env = route_call[1]['env']
        assert route_env['PREFIX'] == off_link_route
        assert route_env['PREFIX_LEN'] == str(prefix_len)
        assert route_env['IFACE'] == 'eth0'
        assert route_env['ROUTER'] == router
        assert route_env['IS_PREFIX'] == "0"

        # Verify logging
        mock_logger.info.assert_any_call(f"🔧 Configuring prefix for {prefix}/{prefix_len}")
        mock_logger.info.assert_any_call(f"🔧 Configuring route for {off_link_route}/{prefix_len}")
        mock_logger.info.assert_any_call("✅ Route configured successfully: Route added successfully\n") 