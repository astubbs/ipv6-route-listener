#!/bin/bash
# Configure IPv6 routes for Matter/Thread devices
# This script is used by the route listener to configure IPv6 routes
# for Matter/Thread device communication.

set -e

# Function to check if a variable is set
check_var() {
    var_name=$1
    if [ -z "${!var_name}" ]; then
        echo "❌ Error: $var_name environment variable is not set"
        exit 1
    fi
}

# Function to validate IPv6 prefix
validate_prefix() {
    if ! echo "$1" | grep -q '^fd[0-9a-fA-F:]*$'; then
        echo "❌ Error: Invalid ULA prefix: $1 (must start with 'fd')"
        exit 1
    fi
}

# Function to validate prefix length
validate_prefix_len() {
    if ! echo "$1" | grep -q '^[0-9]*$'; then
        echo "❌ Error: Invalid prefix length: $1 (must be a number)"
        exit 1
    fi
    if [ "$1" -lt 0 ] || [ "$1" -gt 128 ]; then
        echo "❌ Error: Invalid prefix length: $1 (must be between 0 and 128)"
        exit 1
    fi
}

# Function to validate interface
validate_interface() {
    if ! ip link show "$1" > /dev/null 2>&1; then
        echo "❌ Error: Interface $1 does not exist"
        exit 1
    fi
}

# Function to validate router address
validate_router() {
    if ! echo "$1" | grep -q '^fe80::'; then
        echo "❌ Error: Invalid router address: $1 (must be a link-local address starting with 'fe80::')"
        exit 1
    fi
}

# Check required environment variables
check_var "PREFIX"
check_var "PREFIX_LEN"
check_var "IFACE"
check_var "ROUTER"

# Validate inputs
validate_prefix "$PREFIX"
validate_prefix_len "$PREFIX_LEN"
validate_interface "$IFACE"
validate_router "$ROUTER"

# Log the configuration
echo "🔍 Configuring route: $PREFIX/$PREFIX_LEN via $ROUTER on interface $IFACE"

# Remove any existing routes for this prefix
# This includes both exact matches and higher-order subnets
echo "🧹 Removing any existing routes for $PREFIX and its subnets"

# Extract the base prefix without any length notation
BASE_PREFIX=$(echo "$PREFIX" | sed 's/\/.*$//')

# First, get all existing routes for this prefix
echo "   Checking for existing routes..."
ip -6 route show | grep "$BASE_PREFIX" | while read -r route; do
    if [ -n "$route" ]; then
        echo "   🗑️  Removing: $route"
        # Use eval to properly handle the route string
        eval "ip -6 route del $route" 2>/dev/null || true
    fi
done

# Try to remove any routes with specific prefix lengths
# This handles cases where the route might be specified with a prefix length
echo "   Checking for prefix length routes..."
for LENGTH in 64 48 32 16; do
    echo "   🗑️  Trying /$LENGTH routes..."
    ip -6 route del "$BASE_PREFIX/$LENGTH" 2>/dev/null || true
    ip -6 route del "$BASE_PREFIX/$LENGTH" via "$ROUTER" dev "$IFACE" 2>/dev/null || true
done

# Add the new route with /64 prefix length (standard for ULA)
echo "➕ Adding route to $BASE_PREFIX/64 via $ROUTER on $IFACE"
if ip -6 route add "$BASE_PREFIX/64" via "$ROUTER" dev "$IFACE"; then
    echo "✅ Route added successfully"
else
    echo "❌ Failed to add route"
    exit 1
fi 