#!/usr/bin/env python3
"""Main module for the ICMPv6 RA listener."""

import sys
import subprocess
import os
import argparse
import datetime
from scapy.all import sniff, IPv6, ICMPv6ND_RA, ICMPv6NDOptPrefixInfo, ICMPv6NDOptRouteInfo, conf, get_if_list

# Banner for the application
BANNER = """
╔════════════════════════════════════════════════════════════════════════════╗
║                     🚀 ICMPv6 RA Listener v0.1.0                          ║
║                                                                          ║
║  Monitors Thread Border Routers for IPv6 Router Advertisements           ║
║  and displays ULA prefixes and routes for network configuration          ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

# Track seen routes to avoid duplicate processing
seen_routes = set()

def log(message, prefix=""):
    """Log a message with a timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {prefix}{message}")

def configure_route(prefix, router, iface):
    """Configure a route on the host system using the thread-route.sh script."""
    if not prefix or not router:
        return False
    
    # Create a unique key for this route
    route_key = f"{prefix}|{router}"
    
    # Skip if we've already processed this route
    if route_key in seen_routes:
        log(f"⏭️  Route already configured: {prefix} via {router}", "  ")
        return True
    
    log(f"🔧 Configuring new route: {prefix} via {router}", "  ")
    
    try:
        # Call the thread-route.sh script with the prefix and router
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "thread-route.sh")
        
        # Make sure the script is executable
        os.chmod(script_path, 0o755)
        
        # Run the script with the prefix and router as environment variables
        result = subprocess.run(
            [script_path],
            env={"PREFIX": prefix, "ROUTER": router, "IFACE": iface, **os.environ},
            capture_output=True,
            text=True,
            check=True
        )
        
        log(f"✅ Route configuration output:\n{result.stdout}", "  ")
        
        # Add to seen routes
        seen_routes.add(route_key)
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Error configuring route: {e}", "  ")
        log(f"Error output: {e.stderr}", "  ")
        return False
    except Exception as e:
        log(f"❌ Unexpected error: {e}", "  ")
        return False

def handle_packet(packet):
    """Handle incoming ICMPv6 Router Advertisements packets."""
    if not packet.haslayer(ICMPv6ND_RA):
        return

    ra = packet[ICMPv6ND_RA]
    src = packet[IPv6].src
    log(f"🔔 Router Advertisement from {src}")
    
    # Track prefixes and routes from this RA
    prefixes = []
    routes = []
    
    for opt in ra.iterpayloads():
        if isinstance(opt, ICMPv6NDOptPrefixInfo):
            prefix = opt.prefix
            log(f"📡 Prefix: {prefix}", "  ")
            prefixes.append(prefix)
        elif isinstance(opt, ICMPv6NDOptRouteInfo):
            route = opt.prefix
            log(f"📍 Route: {route}", "  ")
            routes.append(route)
    
    # Configure routes for each prefix
    for prefix in prefixes:
        if prefix.startswith("fd"):  # ULA prefix
            configure_route(prefix, src, args.interface)
    
    # Configure routes for each route
    for route in routes:
        if route.startswith("fd"):  # ULA route
            configure_route(route, src, args.interface)

def main():
    """Main entry point for the RA listener."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ICMPv6 RA listener for Thread route monitoring")
    parser.add_argument("-i", "--interface", default="eth0", 
                        help="Network interface to listen on (default: eth0)")
    global args
    args = parser.parse_args()
    
    log(BANNER)
    
    # Print system information
    log("🔍 System Information:")
    log(f"  Python version: {sys.version}")
    log(f"  Scapy version: {conf.version}")
    
    # List available interfaces
    interfaces = get_if_list()
    log(f"  Available interfaces: {', '.join(interfaces)}")
    
    # Check if the specified interface exists
    if not interfaces:
        log("❌ No network interfaces found!")
        return 1
    
    if args.interface not in interfaces:
        log(f"❌ Error: Interface '{args.interface}' not found!")
        log("  Please specify a valid interface using the -i option.")
        log(f"  Available interfaces: {', '.join(interfaces)}")
        return 1
    
    log(f"📡 Listening for Router Advertisements on interface '{args.interface}'...")
    log("Press Ctrl+C to stop")
    
    # Force output to be flushed immediately
    sys.stdout.flush()
    
    try:
        # Start sniffing
        sniff(filter="icmp6", iface=args.interface, prn=handle_packet)
    except KeyboardInterrupt:
        log("👋 Stopping RA listener...")
    except Exception as e:
        log(f"❌ Error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main()) 