"""Scapy-based packet handler for ICMPv6 Router Advertisements."""

from scapy.all import sniff, IP, IPv6, ICMPv6ND_RA, ICMPv6ND_RS, ICMPv6NDOptPrefixInfo, ICMPv6NDOptRouteInfo, send, conf
from .packet_handler import BasePacketHandler
from .route_info import RouteInfo, RouteInfoProcessor
import threading
import time
import binascii

class ScapyPacketHandler(BasePacketHandler):
    """Scapy-based implementation of ICMPv6 Router Advertisement handler."""
    
    def __init__(self, interface, route_configurator, logger, enable_rs=False, enable_parsing=True):
        """Initialize the packet handler.
        
        Args:
            interface: The network interface to listen on
            route_configurator: The route configurator instance
            logger: The logger instance
            enable_rs: Whether to enable Router Solicitation
            enable_parsing: Whether to enable packet parsing (for testing)
        """
        super().__init__(interface, route_configurator, logger)
        self.route_processor = RouteInfoProcessor(route_configurator, logger)
        self.running = True
        self.enable_rs = enable_rs
        self.enable_parsing = enable_parsing

    def start(self):
        """Start listening for Router Advertisements."""
        self.logger.info(f"📡 Listening for Router Advertisements on interface '{self.interface}'...")
        self.logger.info("Press Ctrl+C to stop")
        
        # Configure Scapy for IPv6
        conf.iface = self.interface
        conf.use_pcap = True  # Use libpcap for better performance
        
        # Start Router Solicitation thread if enabled
        if self.enable_rs:
            rs_thread = threading.Thread(target=self._send_router_solicitations)
            rs_thread.daemon = True
            rs_thread.start()
        
        # Start packet capture with a more specific filter
        self.logger.debug(f"🔍 Starting packet capture on interface '{self.interface}' with filter 'icmp6 and ip6[40] = 134'")
        try:
            # Use a more specific filter for Router Advertisements
            sniff(iface=self.interface, 
                  prn=self._handle_packet, 
                  filter="icmp6 and ip6[40] = 134",  # Filter for ICMPv6 Router Advertisements
                  store=0)
        except Exception as e:
            self._log_error("Error starting packet capture", e)
            # Try to recover by falling back to a simpler filter
            try:
                self.logger.warning("Falling back to basic ICMPv6 filter...")
                sniff(iface=self.interface, 
                      prn=self._handle_packet, 
                      filter="icmp6",  # Basic ICMPv6 filter
                      store=0)
            except Exception as e2:
                self._log_error("Error with fallback packet capture", e2)
                raise
        
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
        self.logger.debug("Got packet, inspecting...")
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
            # Skip processing if parsing is disabled
            if not self.enable_parsing:
                self.logger.debug("⏭️  Packet parsing disabled, skipping processing")
                return

            # Get the Router Advertisement layer
            ra = packet[ICMPv6ND_RA]
            
            # Now we can log the packet details if in debug mode
            if self.logger.verbose:
                self.logger.debug(f"🔍 Raw RA data: {ra.show()}")
                self.logger.debug(f"🔍 RA options: {ra.payload}")
            
            # Extract route information from options
            route_infos = []
            
            # Get all options from the RA packet
            options = ra.payload if hasattr(ra, 'payload') else []
            if isinstance(options, list):
                # If options is a list, process each option
                for opt in options:
                    self._process_option(opt, packet[IPv6].src, route_infos)
            else:
                # If options is a single option or chain, process it
                opt = options
                while opt and not isinstance(opt, bytes):
                    self._process_option(opt, packet[IPv6].src, route_infos)
                    opt = opt.payload if hasattr(opt, 'payload') else None
            
            # Process all route information
            if route_infos:
                self.logger.info(f"🔧 Processing {len(route_infos)} route(s)/prefix(es) from RA")
                self.route_processor.process_route_infos(route_infos)
            elif self.logger.verbose:
                self.logger.debug("⏭️  No route information found in packet")
                    
        except Exception as e:
            if self.logger.verbose:
                self._log_error("Error processing Router Advertisement", e)
                
    def _process_option(self, opt, src_addr, route_infos):
        """Process a single RA option."""
        if self.logger.verbose:
            self.logger.debug(f"🔍 Processing option: {type(opt).__name__}")
            self.logger.debug(f"🔍 Option data: {opt.show()}")
        
        if isinstance(opt, ICMPv6NDOptPrefixInfo):
            try:
                prefix_str = str(opt.prefix)
                prefix_len = opt.prefixlen
                if self.logger.verbose:
                    self.logger.debug(f"🔍 Found on-link prefix: {prefix_str}/{prefix_len}")
                    self.logger.info(f"📡 On-link prefix: {prefix_str}/{prefix_len} (directly connected)")
                route_infos.append(RouteInfo(
                    prefix=prefix_str,
                    prefix_len=prefix_len,
                    router=src_addr,
                    is_prefix=True,
                    valid_time=opt.validlifetime,
                    pref_time=opt.preferredlifetime
                ))
            except AttributeError as e:
                if self.logger.verbose:
                    self.logger.error(f"❌ Error processing prefix option: Missing required attribute - {str(e)}")
                    self.logger.debug(f"Option data: {opt}")
        elif isinstance(opt, ICMPv6NDOptRouteInfo):
            try:
                prefix_str = str(opt.prefix)
                prefix_len = opt.plen  # Route Info uses 'plen' instead of 'prefixlen'
                if self.logger.verbose:
                    self.logger.debug(f"🔍 Found off-link route: {prefix_str}/{prefix_len}")
                    self.logger.info(f"🛣️  Off-link route: {prefix_str}/{prefix_len} (via {src_addr})")
                route_infos.append(RouteInfo(
                    prefix=prefix_str,
                    prefix_len=prefix_len,
                    router=src_addr,
                    is_prefix=False,
                    lifetime=opt.rtlifetime
                ))
            except AttributeError as e:
                if self.logger.verbose:
                    self.logger.error(f"❌ Error processing route option: {str(e)}")
                    self.logger.debug(f"Option data: {opt}")
        else:
            if self.logger.verbose:
                self.logger.debug(f"⏭️  Ignoring option type: {type(opt).__name__}")
            
    def stop(self):
        """Stop the packet handler."""
        self.logger.info("🛑 Stopping packet handler")
        self.running = False 