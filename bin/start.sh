#!/bin/sh

# Parse interface from arguments, fallback to INTERFACE env var or eth0
IFACE="${INTERFACE:-eth0}"
prev=""
for arg in "$@"; do
    if [ "$prev" = "-i" ] || [ "$prev" = "--interface" ]; then
        IFACE="$arg"
    fi
    prev="$arg"
done

# Start the listener in the background
echo "📡 Starting ICMPv6 RA Listener..."
python -u -m route_listener.main "$@" &

# Wait a moment for the server to initialize
sleep 2

# Run rdisc6 to discover routers
echo "🔍 Running router discovery on $IFACE..."
rdisc6 "$IFACE"

# Wait for the listener process
wait 