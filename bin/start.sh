#!/bin/sh

# Start the listener in the background
echo "📡 Starting ICMPv6 RA Listener..."
python -u -m route_listener.main "$@" &

# Wait a moment for the server to initialize
sleep 2

# Run rdisc6 to discover routers
echo "🔍 Running router discovery..."
rdisc6 eth0

# Wait for the listener process
wait 