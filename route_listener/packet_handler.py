"""Base packet handler module for ICMPv6 Router Advertisements."""

from abc import ABC, abstractmethod
from .route_configurator import RouteConfigurator
from .logger import Logger
import logging
import threading
import time

class BasePacketHandler(ABC):
    """Base class for ICMPv6 Router Advertisement handlers."""
    
    def __init__(self, interface: str, route_configurator: RouteConfigurator, logger: Logger, enable_rs: bool = False):
        self.interface = interface
        self.route_configurator = route_configurator
        self.logger = logger
        self.running = True
        self.last_processed = {}  # Track last processed RA from each source
        self.enable_rs = enable_rs  # Flag to enable/disable router solicitation
        
    @abstractmethod
    def start(self):
        """Start listening for Router Advertisements."""
        pass
        
    @abstractmethod
    def stop(self):
        """Stop the packet handler."""
        pass
        
    def _check_duplicate(self, src_addr: str) -> bool:
        """Check if this is a duplicate RA from the same source within 1 second."""
        current_time = time.time()
        if src_addr in self.last_processed:
            last_time = self.last_processed[src_addr]
            if current_time - last_time < 1:
                return True
        self.last_processed[src_addr] = current_time
        return False
        
    def _process_ula_prefix(self, prefix: str, prefix_len: int, router: str = None):
        """Process a ULA prefix."""
        if prefix.startswith("fd"):
            self.logger.info(f"🔍 Found ULA prefix: {prefix}/{prefix_len}")
            self.route_configurator.configure(prefix, prefix_len, router)
        else:
            self.logger.debug(f"⏭️  Ignoring non-ULA prefix: {prefix}/{prefix_len}")
            
    def _log_error(self, message: str, error: Exception):
        """Log an error with debug details if enabled."""
        self.logger.error(f"❌ {message}: {str(error)}")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Error type: {type(error).__name__}")
            self.logger.debug(f"Error details: {str(error)}")
            
    def _start_router_solicitation(self):
        """Start the router solicitation thread if enabled."""
        if self.enable_rs:
            self.logger.info("🔔 Router Solicitation enabled")
            rs_thread = threading.Thread(target=self._send_router_solicitations)
            rs_thread.daemon = True
            rs_thread.start()
        else:
            self.logger.info("🔕 Router Solicitation disabled")
            
    def _send_router_solicitations(self):
        """Send periodic Router Solicitation messages."""
        # This is a placeholder - actual implementation is in the concrete classes
        pass 