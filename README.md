# 🧭 Route Listener for ICMPv6 RAs (Thread Border Routers)

This project listens for IPv6 Router Advertisements (RAs) from Thread Border Routers and automatically configures ULA prefixes and routes on the host system. It's specifically designed for environments like Synology DSM where the kernel is missing support for processing IPv6 route advertisements for Matter/Thread subnets.

## 🎯 Purpose

This tool was created to solve a specific problem when running Home Assistant on a Synology NAS:

1. The Synology DSM kernel is missing the `CONFIG_IPV6_ROUTE_INFO` kernel option
2. This prevents the system from automatically processing IPv6 Router Advertisements for subnets
3. Matter/Thread devices use these subnets for communication
4. Without proper routing, Home Assistant cannot communicate with Matter devices

This project provides a workaround by:
- Listening for ICMPv6 Router Advertisements
- Extracting ULA prefixes and routes
- Manually configuring these routes in the kernel using the `ip` command

## 🚀 Quick Start (with Docker)

1. **Clone this repo:**

    ```bash
    git clone https://github.com/your/repo.git
    cd route-listener
    ```

2. **Build and run the Docker container:**

    ```bash
    # Use default interface (eth0)
    ./run.sh

    # Or specify a custom interface
    ./run.sh -i wlan0
    ```

## 🐍 Local Development

If you're not using Docker:

1. **Install Poetry:**

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2. **Install dependencies:**

    ```bash
    poetry install
    ```

3. **Run the script:**

    ```bash
    # Use default interface (eth0)
    poetry run python -m route_listener.main

    # Or specify a custom interface
    poetry run python -m route_listener.main -i wlan0
    ```

## 💡 How It Works

1. **Route Detection:**
   - Listens for ICMPv6 Router Advertisements on the specified network interface
   - Extracts ULA prefixes and routes from the advertisements
   - Each route is processed only once (subsequent advertisements for the same route are ignored)

2. **Route Configuration:**
   - When a new route is detected, an external script (`thread-route.sh`) is called
   - The script uses the `ip` command to add the route to the kernel
   - Existing routes with the same prefix are removed before adding the new one

3. **Interface Configuration:**
   - By default, the script listens on the `eth0` interface
   - You can specify a different interface using the `-i` option
   - The script will abort if the specified interface doesn't exist

## 📋 Example Output

```
[2023-04-19 10:15:30] 🚀 Starting ICMPv6 RA listener...
[2023-04-19 10:15:30] 📡 Listening for Router Advertisements on interface 'eth0'...
[2023-04-19 10:15:35] 🔔 Router Advertisement from fe80::1234:5678:9abc:def0
[2023-04-19 10:15:35]   📡 Prefix: fd00:1234:5678::/64
[2023-04-19 10:15:35]   🔧 Configuring new route: fd00:1234:5678::/64 via fe80::1234:5678:9abc:def0
[2023-04-19 10:15:35]   ✅ Route configuration output:
[2023-04-19 10:15:35]   🔍 Configuring route: fd00:1234:5678::/64 via fe80::1234:5678:9abc:def0 on interface eth0
[2023-04-19 10:15:35]   ➕ Adding route to fd00:1234:5678::/64 via fe80::1234:5678:9abc:def0 on eth0
[2023-04-19 10:15:35]   ✅ Added
[2023-04-19 10:15:40] 🔔 Router Advertisement from fe80::1234:5678:9abc:def0
[2023-04-19 10:15:40]   📡 Prefix: fd00:1234:5678::/64
[2023-04-19 10:15:40]   ⏭️  Route already configured: fd00:1234:5678::/64 via fe80::1234:5678:9abc:def0
```

## 📜 History

This project was inspired by the discussion in the Home Assistant community about running Matter/Thread devices on a Synology NAS. The Synology DSM kernel is missing the `CONFIG_IPV6_ROUTE_INFO` kernel option, which prevents it from automatically processing IPv6 Router Advertisements for subnets that Matter devices use for communication.

This tool provides a workaround by manually configuring the routes based on the Router Advertisements, allowing Home Assistant to communicate with Matter devices on the Synology NAS.

## 🔗 References

- [Matter Server Docker Container on Synology NAS / Home Assistant Core](https://community.home-assistant.io/t/matter-server-docker-container-on-synology-nas-home-assistant-core/751120/15)
