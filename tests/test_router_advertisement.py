"""Integration tests for Router Advertisement handling."""

import pytest
from unittest.mock import Mock
from route_listener.route_info import RouteInfo, RouteInfoProcessor
from route_listener.route_configurator import RouteConfigurator
from route_listener.logger import Logger

# Test data representing Router Advertisement information
TEST_RAS = [
    {
        "description": "RA with ULA prefix and route",
        "src_ip": "fe80::85e:1f44:c26f:229",
        "prefix": "fd82:cd32:5ad7:ff4a::/64",
        "route": "fd2b:7eb9:619c::/64",
        "prefix_on_link": True,
        "prefix_autonomous": True,
        "prefix_valid_time": 1800,
        "prefix_pref_time": 1800,
        "route_preference": "medium",
        "route_lifetime": 1800
    },
    {
        "description": "RA with non-ULA prefix",
        "src_ip": "fe80::f209:dff:fe35:48a",
        "prefix": "2406:e001:abcd:5600::/64",
        "prefix_on_link": True,
        "prefix_autonomous": False,
        "prefix_valid_time": 86400,
        "prefix_pref_time": 14400
    },
    {
        "description": "RA with ULA prefix only",
        "src_ip": "fe80::86f:3592:d12d:58a5",
        "prefix": "fd82:cd32:5ad7:ff4a::/64",
        "prefix_on_link": True,
        "prefix_autonomous": True,
        "prefix_valid_time": 1800,
        "prefix_pref_time": 1800
    }
]

@pytest.fixture
def mock_route_configurator():
    """Create a mock route configurator."""
    configurator = Mock(spec=RouteConfigurator)
    configurator.is_configured.return_value = False
    return configurator

@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock(spec=Logger)
    logger.verbose = True  # Enable verbose mode for testing
    return logger

@pytest.fixture
def route_processor(mock_route_configurator, mock_logger):
    """Create a route processor with mocked dependencies."""
    return RouteInfoProcessor(mock_route_configurator, mock_logger)

def test_process_ula_prefix_and_route(route_processor, mock_route_configurator):
    """Test processing of a Router Advertisement with ULA prefix and route."""
    # Get test data
    ra_data = TEST_RAS[0]
    
    # Create route info objects
    route_infos = [
        RouteInfo(
            prefix=ra_data["prefix"].split('/')[0],
            prefix_len=int(ra_data["prefix"].split('/')[1]),
            router=ra_data["src_ip"],
            is_prefix=True,
            valid_time=ra_data["prefix_valid_time"],
            pref_time=ra_data["prefix_pref_time"]
        ),
        RouteInfo(
            prefix=ra_data["route"].split('/')[0],
            prefix_len=int(ra_data["route"].split('/')[1]),
            router=ra_data["src_ip"],
            is_prefix=False,
            lifetime=ra_data["route_lifetime"]
        )
    ]
    
    # Process the route information
    route_processor.process_route_infos(route_infos)
    
    # Verify configure was called with correct parameters for prefix
    mock_route_configurator.configure.assert_any_call(
        ra_data["prefix"].split('/')[0],  # base_prefix
        int(ra_data["prefix"].split('/')[1]),  # prefix_len
        ra_data["src_ip"],  # router
        is_prefix=True  # is_prefix
    )
    
    # Verify configure was called with correct parameters for route
    mock_route_configurator.configure.assert_any_call(
        ra_data["route"].split('/')[0],  # base_prefix
        int(ra_data["route"].split('/')[1]),  # prefix_len
        ra_data["src_ip"],  # router
        is_prefix=False  # is_prefix
    )

def test_process_non_ula_prefix(route_processor, mock_route_configurator):
    """Test processing of a Router Advertisement with non-ULA prefix."""
    # Get test data
    ra_data = TEST_RAS[1]
    
    # Create route info object
    route_info = RouteInfo(
        prefix=ra_data["prefix"].split('/')[0],
        prefix_len=int(ra_data["prefix"].split('/')[1]),
        router=ra_data["src_ip"],
        is_prefix=True,
        valid_time=ra_data["prefix_valid_time"],
        pref_time=ra_data["prefix_pref_time"]
    )
    
    # Process the route information
    route_processor.process_route_info(route_info)
    
    # Verify configure was not called (non-ULA prefix should be ignored)
    mock_route_configurator.configure.assert_not_called()

def test_process_existing_route(route_processor, mock_route_configurator):
    """Test processing of a Router Advertisement with already configured route."""
    # Configure mock to return True for is_configured
    mock_route_configurator.is_configured.return_value = True
    
    # Get test data
    ra_data = TEST_RAS[0]
    
    # Create route info object
    route_info = RouteInfo(
        prefix=ra_data["prefix"].split('/')[0],
        prefix_len=int(ra_data["prefix"].split('/')[1]),
        router=ra_data["src_ip"],
        is_prefix=True,
        valid_time=ra_data["prefix_valid_time"],
        pref_time=ra_data["prefix_pref_time"]
    )
    
    # Process the route information
    route_processor.process_route_info(route_info)
    
    # Verify configure was not called (already configured route should be ignored)
    mock_route_configurator.configure.assert_not_called()

def test_process_ula_prefix_only(route_processor, mock_route_configurator):
    """Test processing of a Router Advertisement with only ULA prefix."""
    # Get test data
    ra_data = TEST_RAS[2]
    
    # Create route info object
    route_info = RouteInfo(
        prefix=ra_data["prefix"].split('/')[0],
        prefix_len=int(ra_data["prefix"].split('/')[1]),
        router=ra_data["src_ip"],
        is_prefix=True,
        valid_time=ra_data["prefix_valid_time"],
        pref_time=ra_data["prefix_pref_time"]
    )
    
    # Process the route information
    route_processor.process_route_info(route_info)
    
    # Verify configure was called only for the prefix
    mock_route_configurator.configure.assert_called_once_with(
        ra_data["prefix"].split('/')[0],  # base_prefix
        int(ra_data["prefix"].split('/')[1]),  # prefix_len
        ra_data["src_ip"],  # router
        is_prefix=True  # is_prefix
    )

def test_process_off_link_route(route_processor, mock_route_configurator):
    """Test processing of a Router Advertisement with off-link route."""
    # Create route info object for off-link route
    route_info = RouteInfo(
        prefix="fd2b:7eb9:619c::",
        prefix_len=64,
        router="fe80::85e:1f44:c26f:229",
        is_prefix=False,  # This is an off-link route
        lifetime=1800
    )
    
    # Process the route information
    route_processor.process_route_info(route_info)
    
    # Verify configure was called with correct parameters
    mock_route_configurator.configure.assert_called_once_with(
        "fd2b:7eb9:619c::",  # base_prefix
        64,  # prefix_len
        "fe80::85e:1f44:c26f:229",  # router
        is_prefix=False  # is_prefix
    ) 