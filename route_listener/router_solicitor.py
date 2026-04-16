"""Router Solicitation message handling."""

from scapy.all import Ether, ICMPv6ND_RS, ICMPv6NDOptSrcLLAddr, IPv6, sendp

from .logger import Logger


class RouterSolicitor:
    """Handles sending Router Solicitation messages."""

    def __init__(self, interface: str, logger: Logger | None = None) -> None:
        """Initialize the router solicitor.

        Args:
            interface: Network interface to use
            logger: Optional logger instance for debug output
        """
        self.interface = interface
        self.logger = logger

    def send(self) -> None:
        """Send a Router Solicitation message."""
        try:
            # Create the Router Solicitation packet
            rs = IPv6(dst="ff02::2") / ICMPv6ND_RS()

            # Add source link-layer address option
            rs = rs / ICMPv6NDOptSrcLLAddr()

            # Send the packet
            if self.logger:
                self.logger.debug("📤 Sending Router Solicitation")
                self.logger.debug(f"🔍 RS packet: {rs.show()}")

            sendp(Ether() / rs, iface=self.interface, verbose=0)

            if self.logger:
                self.logger.info("📤 Router Solicitation sent")

        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Error sending Router Solicitation: {e!s}")
