FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    tcpdump iproute2 libcap2-bin \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy poetry files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install poetry and dependencies
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-root

# Copy the rest of the application
COPY . .

# Install the project itself
RUN poetry install --no-interaction

# Make the thread-route.sh script executable
RUN chmod +x thread-route.sh

# Enable low-level packet capture (needed for scapy)
RUN setcap cap_net_raw,cap_net_admin=eip $(readlink -f $(which python3))

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Run the script
CMD ["python", "-u", "-m", "route_listener.main"]