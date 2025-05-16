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
    # Use default interface (ovs_eth0)
    ./run.sh

    # Or specify a custom interface
    ./run.sh -i eth0

    # Enable verbose logging
    ./run.sh --verbose

    # Enable debug logging
    ./run.sh --debug
    ```

    You can also configure the interface using environment variables:
    ```bash
    # Using environment variable
    docker run -e INTERFACE=eth0 ...

    # Or with docker-compose
    docker-compose up -e INTERFACE=eth0
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
    poetry run route-listen

    # Or specify a custom interface
    poetry run route-listen -i eth0

    # Enable debug logging
    poetry run route-listen -i eth0 --debug

    # Enable verbose logging
    poetry run route-listen --verbose
    ```

    Note: Since this tool needs to capture network packets, you might need to run it with sudo:

    ```bash
    sudo poetry run route-listen -i eth0 --debug
    ```

    Available options:
    - `-i, --interface`: Specify the network interface to listen on (default: eth0)
    - `--debug`: Enable detailed debug logging
    - `--verbose`: Enable verbose logging output

## 💡 How It Works

1. **Route Detection:**
   - Listens for ICMPv6 Router Advertisements on the specified network interface
   - Extracts ULA prefixes and routes from the advertisements
   - Each route is processed only once (subsequent advertisements for the same route are ignored)
   - If multiple routes are advertised for the same subnet, the last route wins

2. **Route Filtering:**
   - Only ULA prefixes (starting with 'fd') are configured
   - Non-ULA prefixes are ignored by default
   - You can enable logging of ignored routes with the `--log-ignored` option
   - **Why only ULA prefixes?** Matter/Thread devices use ULA (Unique Local Address) prefixes for their internal communication. These prefixes are guaranteed to be unique and are not routable on the public internet, making them ideal for local network communication. By filtering for only ULA prefixes, we ensure we're only configuring routes that are relevant for Matter/Thread device communication.

3. **Router Discovery:**
   - The application uses `rdisc6` to send an initial Router Solicitation message
   - This helps discover routers that might not be advertising regularly
   - The tool then passively listens for Router Advertisements
   - No periodic Router Solicitation is sent to minimize network traffic

4. **Route Configuration:**
   - When a new ULA route is detected, an external script (`configure-ipv6-route.sh`) is called
   - The script uses the `ip` command to add the route to the kernel
   - Existing routes with the same prefix are removed before adding the new one
   - If multiple routes are advertised for the same subnet, the last route wins

## Router Advertisement Prefix Types

Router Advertisements can contain two types of prefix information:

1. **On-link Prefix (PIO - Prefix Information Option)**
   - Indicates that the prefix is directly connected to the link
   - Used for addresses that can be reached directly on the local network
   - Example: `fd82:cd32:5ad7:ff4a::/64`

2. **Off-link Prefix (RIO - Route Information Option)**
   - Indicates that the prefix is reachable through the advertising router
   - Used for routes that need to go through the router to reach
   - Example: `fd2b:7eb9:619c::/64`

Both types of prefixes are important for proper IPv6 routing configuration.

## 📋 Example Output

```
[2023-04-19 10:15:30] 🚀 Starting ICMPv6 RA listener...
[2023-04-19 10:15:30] 📡 Listening for Router Advertisements on interface 'eth0'...
[2023-04-19 10:15:35] 🔔 Router Advertisement from fe80::1234:5678:9abc:def0
[2023-04-19 10:15:35]   📡 On-link prefix: fd00:1234:5678::/64 (directly connected)
[2023-04-19 10:15:35]   🛣️  Off-link route: fd2b:7eb9:619c::/64 (via fe80::1234:5678:9abc:def0)
[2023-04-19 10:15:35]   🔧 Processing 2 route(s)/prefix(es) from RA
[2023-04-19 10:15:35]   ✅ Route configuration output:
[2023-04-19 10:15:35]   🔍 Configuring route: fd00:1234:5678::/64 via fe80::1234:5678:9abc:def0 on interface eth0
[2023-04-19 10:15:35]   ➕ Adding route to fd00:1234:5678::/64 via fe80::1234:5678:9abc:def0 on eth0
[2023-04-19 10:15:35]   ✅ Added
```

## 📜 History

This project was inspired by the discussion in the Home Assistant community about running Matter/Thread devices on a Synology NAS. The Synology DSM kernel is missing the `CONFIG_IPV6_ROUTE_INFO` kernel option, which prevents it from automatically processing IPv6 Router Advertisements for subnets that Matter devices use for communication.

This tool provides a workaround by manually configuring the routes based on the Router Advertisements, allowing Home Assistant to communicate with Matter devices on the Synology NAS.

## 🔗 References

- [Matter Server Docker Container on Synology NAS / Home Assistant Core](https://community.home-assistant.io/t/matter-server-docker-container-on-synology-nas-home-assistant-core/751120/15)

## Verification Tools

This project includes several tools to ensure code quality and consistency:

### Prerequisites

Before running any verification tools, make sure you have installed the project dependencies:

```bash
# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### Makefile

The project includes a Makefile with targets for verification:

```bash
# Run all verification steps (format, lint, test, type-check)
make verify

# Run verification in check-only mode (for CI)
make verify-check

# Run individual steps
make format
make lint
make test
make type-check
```

### Verification Script

A simple script is provided to run the Makefile commands:

```bash
# Run verification in fix mode (for local development)
./scripts/verify.sh

# Run verification in check-only mode (for CI)
./scripts/verify.sh --check
```

### Test Guidelines

See [tests/README.md](tests/README.md) for detailed guidelines on writing and maintaining tests, including:
- Best practices for test design
- How to write resilient tests
- Examples from our codebase
- Common pitfalls to avoid

### Pre-commit Hooks

Pre-commit hooks automatically run verification steps when you commit changes:

1. Install pre-commit:
   ```bash
   pip install pre-commit
   ```

2. Install the hooks:
   ```bash
   pre-commit install
   ```

3. (Optional) Run hooks on all files:
   ```bash
   pre-commit run --all-files
   ```

### GitHub Actions

The project includes a GitHub Actions workflow that runs verification on:
- Every push to the main branch
- Every pull request to the main branch

This ensures that all code in the repository meets quality standards.
