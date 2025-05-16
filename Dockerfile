FROM python:3.11-slim

# Install required packages:
#   iproute2     - Required for 'ip' command to manage IPv6 routes
#   ndisc6       - Provides rdisc6 tool for sending Router Solicitations
#   tcpdump      - Useful for debugging network traffic
#   libpcap-dev  - Required by Scapy for packet capture
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iproute2 \
    ndisc6 \
    tcpdump \
    libpcap-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy poetry files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install poetry and dependencies
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-root --with dev

# Install code quality tools
RUN pip install --no-cache-dir \
    ruff \
    mypy \
    radon \
    pylint

# Copy the rest of the application
COPY . .

# Install the project itself
RUN poetry install --no-interaction

# Make scripts executable
RUN chmod +x bin/*

# Enable low-level packet capture (needed for scapy)
RUN setcap cap_net_raw,cap_net_admin=eip $(readlink -f $(which python3))

# Default command (can be overridden)
ENV INTERFACE=ovs_eth0
CMD ["/bin/sh", "bin/start.sh", "-i", "${INTERFACE}"]