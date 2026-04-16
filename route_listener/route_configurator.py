"""Route configuration module for IPv6 routes."""

import os
import subprocess
from dataclasses import dataclass

from .config import DEFAULT_INTERFACE
from .logger import Logger


@dataclass
class Route:
    """Represents an IPv6 route."""

    prefix: str
    router: str | None
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
        base_prefix = self.prefix.split("/")[0]
        return f"{base_prefix}|{self.router}|{self.interface}|{self.is_prefix}"


class RouteExecutor:
    """Handles the actual execution of route configuration commands."""

    def __init__(self, logger: Logger, interface: str = DEFAULT_INTERFACE):
        """Initialize route executor.

        Args:
            logger: Logger instance for output
            interface: Network interface to use (default: eth0)
        """
        self.logger = logger
        self.interface = interface
        self.script_path = os.path.join(
            os.path.dirname(__file__), "..", "bin", "configure-ipv6-route.sh"
        )

    def execute(self, route: Route, prefix_len: int) -> bool:
        """Execute the route configuration command.

        Args:
            route: The route to configure
            prefix_len: Prefix length

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        try:
            # Set environment variables for the script
            env = os.environ.copy()
            env["PREFIX"] = route.prefix
            env["PREFIX_LEN"] = str(prefix_len)
            env["IFACE"] = self.interface
            if route.router:
                env["ROUTER"] = route.router
            env["IS_PREFIX"] = "1" if route.is_prefix else "0"

            # Log the parameters before running the script
            self.logger.info("🔍 Running script with parameters:")
            self.logger.info(f"   PREFIX: {route.prefix}")
            self.logger.info(f"   PREFIX_LEN: {prefix_len}")
            self.logger.info(f"   IFACE: {self.interface}")
            if route.router:
                self.logger.info(f"   ROUTER: {route.router}")
            else:
                self.logger.error("⚠️  No router address provided")
            self.logger.info(f"   TYPE: {'prefix' if route.is_prefix else 'route'}")

            # Run the script and capture output
            result = subprocess.run(
                [self.script_path], env=env, capture_output=True, text=True, check=False
            )

            # Check the return code
            kind = "Prefix" if route.is_prefix else "Route"
            kind_lower = "prefix" if route.is_prefix else "route"
            if result.returncode == 0:
                self.logger.info(f"✅ {kind} configured successfully: {result.stdout}")
                return True
            else:
                self.logger.error(f"❌ Failed to configure {kind_lower}: {result.stderr}")
                self.logger.debug(f"Command output: {result.stdout}")
                self.logger.debug(f"Command error: {result.stderr}")
                self.logger.debug(f"Return code: {result.returncode}")
                return False

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Script execution failed: {e!s}")
            self.logger.debug(f"Command output: {e.stdout}")
            self.logger.debug(f"Command error: {e.stderr}")
            self.logger.debug(f"Return code: {e.returncode}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected error during route configuration: {e!s}")
            self.logger.debug(f"Error details: {e!s}")
            return False


class RouteConfigurator:
    """Handles IPv6 route configuration."""

    def __init__(self, logger: Logger, interface: str = DEFAULT_INTERFACE):
        """Initialize route configurator.

        Args:
            logger: Logger instance for output
            interface: Network interface to use (default: eth0)
        """
        self.logger = logger
        self.interface = interface
        self.seen_routes: set[str] = set()
        self.executor = RouteExecutor(logger, interface)

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

    def configure(
        self,
        prefix: str,
        prefix_len: int,
        router: str | None = None,
        is_prefix: bool = False,
    ) -> None:
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
            self.logger.info(
                f"⏭️  {'Prefix' if is_prefix else 'Route'} already configured: {prefix}/{prefix_len}"
            )
            return

        self.logger.info(
            f"🔧 Configuring {'prefix' if is_prefix else 'route'} for {prefix}/{prefix_len}"
        )

        # Execute the route configuration
        if self.executor.execute(route, prefix_len):
            self.seen_routes.add(route_key)

    def get_route_key(self, prefix: str, router: str | None = None) -> str:
        """Generate a unique key for a route.

        Args:
            prefix: IPv6 prefix
            router: Router address (optional)

        Returns:
            A unique string key for the route
        """
        # Remove any existing prefix length notation
        base_prefix = prefix.split("/")[0]
        if router:
            return f"{base_prefix}|{router}|{self.interface}"
        return f"{base_prefix}|{self.interface}"

    def process_packet_info(self, packet_info: dict) -> None:
        """Process packet information from a Router Advertisement.

        Args:
            packet_info: Dictionary containing packet information:
                - src_ip: Source IP address of the Router Advertisement
                - prefix: Optional prefix information dictionary
                - route: Optional route information dictionary
        """
        src_ip = packet_info["src_ip"]

        # Process prefix if present
        if "prefix" in packet_info:
            prefix_info = packet_info["prefix"]
            prefix = prefix_info["address"]
            prefix_len = prefix_info["length"]

            # Only configure ULA prefixes
            if prefix.startswith("fd"):
                self.configure(prefix, prefix_len, router=src_ip, is_prefix=True)

        # Process route if present
        if "route" in packet_info:
            route_info = packet_info["route"]
            route = route_info["address"]
            route_len = route_info["length"]

            # Only configure ULA routes
            if route.startswith("fd"):
                self.configure(route, route_len, router=src_ip, is_prefix=False)
