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

    def __str__(self) -> str:
        return f"{self.prefix} via {self.router}"

    def is_ula(self) -> bool:
        """Check if this is a ULA prefix (starts with 'fd')."""
        return self.prefix.startswith("fd")
    
    def get_route_key(self) -> str:
        """Get a unique key for this route."""
        # Remove any existing prefix length notation
        base_prefix = self.prefix.split('/')[0]
        return f"{base_prefix}|{self.router}"

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
        
    def configure(self, prefix: str, prefix_len: int, router: str = None) -> None:
        """Configure a route for the given prefix.
        
        Args:
            prefix: IPv6 prefix to configure
            prefix_len: Prefix length
            router: Router address (optional)
        """
        # Skip if we've seen this route before
        route_key = self.get_route_key(prefix, router)
        if route_key in self.seen_routes:
            self.logger.info(f"⏭️  Route already configured: {prefix}/{prefix_len}")
            return
            
        self.logger.info(f"🔧 Configuring route for {prefix}/{prefix_len}")
        
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
                
            # Log the parameters before running the script
            self.logger.info(f"🔍 Running script with parameters:")
            self.logger.info(f"   PREFIX: {prefix}")
            self.logger.info(f"   PREFIX_LEN: {prefix_len}")
            self.logger.info(f"   IFACE: {self.interface}")
            if router:
                self.logger.info(f"   ROUTER: {router}")
            else:
                self.logger.warning("⚠️  No router address provided")
                
            result = subprocess.run(
                [script_path],
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"✅ Route configured successfully: {result.stdout}")
            self.seen_routes.add(route_key)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Failed to configure route: {e.stderr}")
            
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