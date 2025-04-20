"""Scapy-based packet handler for ICMPv6 Router Advertisements."""

from scapy.all import sniff, IP, IPv6, ICMPv6ND_RA, ICMPv6ND_RS, ICMPv6NDOptPrefixInfo, ICMPv6NDOptRouteInfo, send, conf
from .packet_handler import BasePacketHandler
import threading
import time
import binascii

class ScapyPacketHandler(BasePacketHandler):
    """Scapy-based implementation of ICMPv6 Router Advertisement handler."""
    
    def start(self):
        """Start listening for Router Advertisements."""
        self.logger.info(f"📡 Listening for Router Advertisements on interface '{self.interface}'...")
        self.logger.info("Press Ctrl+C to stop")
        
        # Configure Scapy for IPv6
        conf.iface = self.interface
        conf.use_pcap = True  # Use libpcap for better performance
        
        # Start Router Solicitation thread
        rs_thread = threading.Thread(target=self._send_router_solicitations)
        rs_thread.daemon = True
        rs_thread.start()
        
        # Start packet capture with a more specific filter
        self.logger.debug(f"🔍 Starting packet capture on interface '{self.interface}' with filter 'icmp6 and ip6[40] = 134'")
        sniff(iface=self.interface, 
              prn=self._handle_packet, 
              filter="icmp6 and ip6[40] = 134",  # Only Router Advertisements
              store=0)
        
    def _send_router_solicitations(self):
        """Periodically send Router Solicitation messages."""
        self.logger.debug("🔄 Starting Router Solicitation thread")
        while self.running:
            try:
                self.logger.debug("🔔 Sending Router Solicitation...")
                # Create Router Solicitation with proper IPv6 layer
                rs = IPv6(dst="ff02::2")/ICMPv6ND_RS()
                send(rs, iface=self.interface, verbose=False)
                self.logger.debug("✅ Router Solicitation sent successfully")
                time.sleep(5)  # Send every 5 seconds
            except Exception as e:
                self._log_error("Error sending Router Solicitation", e)
        
    def _handle_packet(self, packet):
        """Handle received packets."""
        try:
            # Ensure we have an IPv6 packet
            if not IPv6 in packet:
                self.logger.debug("⏭️  Ignoring non-IPv6 packet")
                return
                
            # Check if it's a Router Advertisement
            if not ICMPv6ND_RA in packet:
                self.logger.debug("⏭️  Ignoring non-RA packet")
                return
                
            src_addr = packet[IPv6].src
            
            # Check for duplicate RAs
            if self._check_duplicate(src_addr):
                self.logger.debug(f"⏭️  Ignoring duplicate RA from {src_addr}")
                return
                
            self.logger.info(f"🔔 Router Advertisement from {src_addr}")
            
            # Log packet details for debugging
            self.logger.debug(f"📦 Packet data: {binascii.hexlify(bytes(packet)).decode()}")
            
            # Process the Router Advertisement
            self._process_router_advertisement(packet)
            
        except Exception as e:
            self._log_error("Error handling packet", e)
            
    def _process_router_advertisement(self, packet):
        """Process a Router Advertisement packet."""
        try:
            # Get the Router Advertisement layer
            ra = packet[ICMPv6ND_RA]
            
            # Check if the packet has the expected structure
            if not hasattr(ra, 'payload'):
                self.logger.debug("❌ No payload in Router Advertisement")
                return
                
            self.logger.debug(f"🔍 Processing Router Advertisement options: {ra.payload}")
            
            # Extract prefix and route information from options
            for opt in ra.payload:
                self.logger.debug(f"🔍 Processing option: {type(opt).__name__}")
                
                if isinstance(opt, ICMPv6NDOptPrefixInfo):
                    prefix_str = str(opt.prefix)
                    prefix_len = opt.prefixlen
                    self.logger.debug(f"🔍 Found prefix: {prefix_str}/{prefix_len}")
                    if prefix_str.startswith("fd"):
                        self.logger.debug(f"🔍 Found ULA prefix: {prefix_str}/{prefix_len}")
                        self._process_ula_prefix(prefix_str, prefix_len, packet[IPv6].src)
                    else:
                        self.logger.debug(f"⏭️  Ignoring non-ULA prefix: {prefix_str}/{prefix_len}")
                elif isinstance(opt, ICMPv6NDOptRouteInfo):
                    prefix_str = str(opt.prefix)
                    prefix_len = opt.prefixlen
                    self.logger.debug(f"🔍 Found route: {prefix_str}/{prefix_len}")
                    if prefix_str.startswith("fd"):
                        self.logger.debug(f"🔍 Found ULA route: {prefix_str}/{prefix_len}")
                        self._process_ula_route(prefix_str, prefix_len, packet[IPv6].src)
                    else:
                        self.logger.debug(f"⏭️  Ignoring non-ULA route: {prefix_str}/{prefix_len}")
                else:
                    self.logger.debug(f"⏭️  Ignoring option type: {type(opt).__name__}")
                    
        except Exception as e:
            self._log_error("Error processing Router Advertisement", e)
            
    def _process_ula_route(self, prefix: str, prefix_len: int, router: str = None):
        """Process a ULA route (distinct from a prefix)."""
        if prefix.startswith("fd"):
            # Ensure the prefix doesn't already include a length
            base_prefix = prefix.split('/')[0]
            self.logger.info(f"🔍 Found ULA route: {base_prefix}/{prefix_len}")
            self.route_configurator.configure(base_prefix, prefix_len, router)
        else:
            self.logger.debug(f"⏭️  Ignoring non-ULA route: {prefix}/{prefix_len}")
            
    def stop(self):
        """Stop the packet handler."""
        self.logger.info("🛑 Stopping packet handler")
        self.running = False 