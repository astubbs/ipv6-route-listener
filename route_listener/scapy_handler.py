"""Scapy packet handling for IPv6 Router Advertisements."""

from typing import Any

from scapy.all import ICMPv6ND_RA, IPv6, sniff

from .logger import Logger
from .packet_parser import PacketParser
from .route_configurator import RouteConfigurator
from .router_solicitor import RouterSolicitor


class ScapyPacketHandler:
    """Handles IPv6 Router Advertisement packets using Scapy."""

    def __init__(
        self,
        interface: str,
        route_configurator: RouteConfigurator,
        logger: Logger,
        enable_rs: bool = True,
    ):
        """Initialize the packet handler.

        Args:
            interface: Network interface to listen on
            route_configurator: RouteConfigurator instance for handling routes
            logger: Logger instance for output
            enable_rs: Whether to enable Router Solicitation
        """
        self.interface = interface
        self.route_configurator = route_configurator
        self.logger = logger
        self.packet_parser = PacketParser()
        self.router_solicitor = RouterSolicitor(interface, logger) if enable_rs else None

    def start(self) -> None:
        """Start listening for Router Advertisements."""
        self.logger.info(f"🎧 Starting to listen for Router Advertisements on {self.interface}")

        # Send Router Solicitation if enabled
        if self.router_solicitor:
            self.router_solicitor.send()

        # Start sniffing for Router Advertisements
        sniff(
            iface=self.interface,
            filter="icmp6 and ip6[40] = 134",  # ICMPv6 Router Advertisement
            prn=self._handle_packet,
            store=0,
        )

    def _handle_packet(self, packet: Any) -> None:
        """Handle a received packet.

        Args:
            packet: Scapy packet object
        """
        try:
            # Check if it's an IPv6 packet
            if not packet.haslayer(IPv6):
                self.logger.debug("Ignoring non-IPv6 packet")
                return

            # Check if it's a Router Advertisement
            if not packet.haslayer(ICMPv6ND_RA):
                self.logger.debug("Ignoring non-RA packet")
                return

            # Log packet details in debug mode
            self.logger.debug(f"Received RA packet: {packet.summary()}")

            # Parse the packet
            packet_info = self.packet_parser.parse(packet)

            # Process the packet info
            self.route_configurator.process_packet_info(packet_info)

            # Log successful processing
            self.logger.info("✅ Processed Router Advertisement")

        except Exception as e:
            self.logger.error(f"❌ Error processing packet: {e!s}")
            self.logger.debug(f"Packet details: {packet.summary()}")
