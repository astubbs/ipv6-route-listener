"""Route configuration module for IPv6 routes."""

import os
import subprocess
import re
from typing import Optional, Dict, Set
from dataclasses import dataclass
from .logger import Logger
from .router_discovery import RouterDiscovery

@dataclass
class Route:
    """Represents an IPv6 route."""
    prefix: str
    router: str
    interface: str
    is_prefix: bool = False  # Whether this is a prefix (on-link) or route (off-link)

    def __str__(self) -> str:
        return f"{self.prefix} via {self.router} ({'prefix' if self.is_prefix else 'route'})"

    def is_ula(self) -> bool:
        """Check if this is a ULA prefix (starts with 'fd')."""
        return self.prefix.startswith("fd")
    
    def get_route_key(self) -> str:
        """Get a unique key for this route."""
        # Remove any existing prefix length notation
        base_prefix = self.prefix.split('/')[0]
        return f"{base_prefix}|{self.router}|{self.interface}|{self.is_prefix}"

class RouteConfigurator:
    """Handles IPv6 route configuration."""
    
    def __init__(self, logger: Logger, interface: str = "eth0"):
        """Initialize route configurator.
        
        Args:
            logger: Logger instance for output
            interface: Network interface to use (default: eth0)
        """
        self.logger = logger
        self.interface = interface
        self.seen_routes = set()
        
    def is_configured(self, prefix: str, prefix_len: int, is_prefix: bool = False) -> bool:
        """Check if a route is already configured.
        
        Args:
            prefix: IPv6 prefix to check
            prefix_len: Prefix length
            is_prefix: Whether this is a prefix (on-link) or route (off-link)
            
        Returns:
            bool: True if the route is already configured, False otherwise
        """
        # Create a Route object to get the route key
        route = Route(prefix, None, self.interface, is_prefix)
        route_key = route.get_route_key()
        return route_key in self.seen_routes
        
    def configure(self, prefix: str, prefix_len: int, router: str = None, is_prefix: bool = False) -> None:
        """Configure a route for the given prefix.
        
        Args:
            prefix: IPv6 prefix to configure
            prefix_len: Prefix length
            router: Router address (optional)
            is_prefix: Whether this is a prefix (on-link) or route (off-link)
        """
        # Create a Route object
        route = Route(prefix, router, self.interface, is_prefix)
        
        # Skip if we've seen this route before
        route_key = route.get_route_key()
        if route_key in self.seen_routes:
            self.logger.info(f"⏭️  {'Prefix' if is_prefix else 'Route'} already configured: {prefix}/{prefix_len}")
            return
            
        self.logger.info(f"🔧 Configuring {'prefix' if is_prefix else 'route'} for {prefix}/{prefix_len}")
        
        # Run the shell script to configure the route
        script_path = os.path.join(os.path.dirname(__file__), "..", "bin", "configure-ipv6-route.sh")
        try:
            # Set environment variables for the script
            env = os.environ.copy()
            env["PREFIX"] = prefix
            env["PREFIX_LEN"] = str(prefix_len)
            env["IFACE"] = self.interface
            if router:
                env["ROUTER"] = router
            env["IS_PREFIX"] = "1" if is_prefix else "0"
                
            # Log the parameters before running the script
            self.logger.info(f"🔍 Running script with parameters:")
            self.logger.info(f"   PREFIX: {prefix}")
            self.logger.info(f"   PREFIX_LEN: {prefix_len}")
            self.logger.info(f"   IFACE: {self.interface}")
            if router:
                self.logger.info(f"   ROUTER: {router}")
            else:
                self.logger.warning("⚠️  No router address provided")
            self.logger.info(f"   TYPE: {'prefix' if is_prefix else 'route'}")
                
            result = subprocess.run(
                [script_path],
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"✅ {'Prefix' if is_prefix else 'Route'} configured successfully: {result.stdout}")
            self.seen_routes.add(route_key)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Failed to configure {'prefix' if is_prefix else 'route'}: {e.stderr}")
            if self.logger.verbose:
                self.logger.debug(f"Command output: {e.stdout}")
                self.logger.debug(f"Command error: {e.stderr}")
                self.logger.debug(f"Return code: {e.returncode}")
            
    def get_route_key(self, prefix: str, router: str = None) -> str:
        """Generate a unique key for a route.
        
        Args:
            prefix: IPv6 prefix
            router: Router address (optional)
            
        Returns:
            A unique string key for the route
        """
        # Remove any existing prefix length notation
        base_prefix = prefix.split('/')[0]
        if router:
            return f"{base_prefix}|{router}|{self.interface}"
        return f"{base_prefix}|{self.interface}" 