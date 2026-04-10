#!/usr/bin/env python3
"""Main module for the ICMPv6 RA Listener."""

import argparse
import logging
import platform

from scapy.all import conf, get_if_list

from .config import DEFAULT_INTERFACE
from .logger import Logger
from .route_configurator import RouteConfigurator
from .scapy_handler import ScapyPacketHandler

# Version and build information
VERSION = "0.1.0"
BUILD_NUMBER = "4"

def main():
    """Main entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ICMPv6 RA Listener for IPv6 route configuration")
    parser.add_argument("-i", "--interface", default=DEFAULT_INTERFACE, help="Network interface to monitor")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--enable-rs", action="store_true", help="Enable Router Solicitation")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging output")
    args = parser.parse_args()
    
    # Create logger
    logger = Logger(verbose=args.verbose)
    
    # Enable debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Display banner
    logger.banner(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                     🚀 ICMPv6 RA Listener v{VERSION} (build={BUILD_NUMBER})                          ║
║                                                                          ║
║  Monitors Thread Border Routers for IPv6 Router Advertisements           ║
║  and displays ULA prefixes and routes for network configuration          ║
╚════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Display system information
    logger.info("🔍 System Information:")
    logger.info(f"  Python version: {platform.python_version()} ({platform.python_implementation()}, {platform.python_compiler()})")
    logger.info(f"  Scapy version: {conf.version}")
    logger.info(f"  Debug logging: {'Yes' if args.debug else 'No'}")
    logger.info(f"  Verbose mode: {'Yes' if args.verbose else 'No'}")
    logger.info(f"  Available interfaces: {', '.join(get_if_list())}")
    logger.info(f"  Router Solicitation: {'Enabled' if args.enable_rs else 'Disabled'}")
    
    # Initialize route configurator
    configurator = RouteConfigurator(logger, interface=args.interface)
    
    # Initialize packet handler
    handler = ScapyPacketHandler(args.interface, configurator, logger, enable_rs=args.enable_rs)
    
    # Start listening for packets
    handler.start()
    
    return 0

if __name__ == "__main__":
    exit(main()) 