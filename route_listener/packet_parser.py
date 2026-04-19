"""Packet parsing for Router Advertisements."""

from typing import Any

from scapy.all import ICMPv6ND_RA, ICMPv6NDOptPrefixInfo, ICMPv6NDOptRouteInfo, IPv6

from .logger import Logger


class PacketParser:
    """Handles parsing of Router Advertisement packets."""

    def __init__(self, logger: Logger | None = None) -> None:
        """Initialize the packet parser.

        Args:
            logger: Optional logger instance for debug output
        """
        self.logger = logger

    def parse(self, packet: Any) -> dict[str, Any]:
        """Parse a Router Advertisement packet.

        Args:
            packet: The packet to parse

        Returns:
            dict: Dictionary containing packet information:
                - src_ip: Source IP address of the Router Advertisement
                - prefixes: List of prefix information dictionaries (may be empty)
                - routes: List of route information dictionaries (may be empty)

        A single RA can carry multiple PrefixInfo and RouteInfo options, so both
        keys are always lists - callers must iterate.

        Raises:
            Exception: If the packet is malformed or contains invalid options
        """
        try:
            # Ensure we have an IPv6 packet
            if IPv6 not in packet:
                if self.logger:
                    self.logger.debug("⏭️  Ignoring non-IPv6 packet")
                return {}

            # Check if it's a Router Advertisement
            if ICMPv6ND_RA not in packet:
                if self.logger:
                    self.logger.debug("⏭️  Ignoring non-RA packet")
                return {}

            src_addr = packet[IPv6].src

            # Get the Router Advertisement layer
            ra = packet[ICMPv6ND_RA]

            # Now we can log the packet details if in debug mode
            if self.logger:
                self.logger.debug(f"🔍 Raw RA data: {ra.show()}")
                self.logger.debug(f"🔍 RA options: {ra.payload}")

            # Initialize packet info dictionary. prefixes/routes are lists
            # because a single RA can carry multiple PrefixInfo/RouteInfo options.
            packet_info: dict[str, Any] = {
                "src_ip": src_addr,
                "prefixes": [],
                "routes": [],
            }

            # Get all options from the RA packet
            options = ra.payload if hasattr(ra, "payload") else []
            if isinstance(options, list):
                # If options is a list, process each option
                for opt in options:
                    self._process_option(opt, packet_info)
            else:
                # If options is a single option or chain, process it
                opt = options
                while opt and not isinstance(opt, bytes):
                    self._process_option(opt, packet_info)
                    opt = opt.payload if hasattr(opt, "payload") else None

            return packet_info

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error parsing packet: {e!s}")
            raise

    def _process_option(self, opt: Any, packet_info: dict[str, Any]) -> None:  # noqa: PLR0912
        """Process a single RA option.

        Args:
            opt: The option to process
            packet_info: Dictionary to store the parsed information

        Raises:
            Exception: If the option is malformed or contains invalid data
        """
        if self.logger:
            self.logger.debug(f"🔍 Processing option: {type(opt).__name__}")
            self.logger.debug(f"🔍 Option data: {opt.show()}")

        if isinstance(opt, ICMPv6NDOptPrefixInfo):
            # Check for None values
            if opt.prefix is None:
                raise ValueError("Prefix option has None prefix")
            if opt.prefixlen is None:
                raise ValueError("Prefix option has None prefixlen")
            if opt.validlifetime is None:
                raise ValueError("Prefix option has None validlifetime")
            if opt.preferredlifetime is None:
                raise ValueError("Prefix option has None preferredlifetime")

            prefix_str = str(opt.prefix)
            prefix_len = opt.prefixlen
            if self.logger:
                self.logger.debug(f"🔍 Found on-link prefix: {prefix_str}/{prefix_len}")
                self.logger.debug(
                    f"📡 On-link prefix: {prefix_str}/{prefix_len} (directly connected)"
                )
            packet_info["prefixes"].append(
                {
                    "address": prefix_str,
                    "length": prefix_len,
                    "on_link": True,
                    "autonomous": True,
                    "valid_time": opt.validlifetime,
                    "pref_time": opt.preferredlifetime,
                }
            )
        elif isinstance(opt, ICMPv6NDOptRouteInfo):
            # Check for None values
            if opt.prefix is None:
                raise ValueError("Route option has None prefix")
            if opt.plen is None:
                raise ValueError("Route option has None plen")
            if opt.rtlifetime is None:
                raise ValueError("Route option has None rtlifetime")

            prefix_str = str(opt.prefix)
            prefix_len = opt.plen  # Route Info uses 'plen' instead of 'prefixlen'
            if self.logger:
                self.logger.debug(f"🔍 Found off-link route: {prefix_str}/{prefix_len}")
                self.logger.debug(
                    f"🛣️  Off-link route: {prefix_str}/{prefix_len} (via {packet_info['src_ip']})"
                )
            packet_info["routes"].append(
                {
                    "address": prefix_str,
                    "length": prefix_len,
                    "lifetime": opt.rtlifetime,
                }
            )
        elif self.logger:
            self.logger.debug(f"⏭️  Ignoring option type: {type(opt).__name__}")
