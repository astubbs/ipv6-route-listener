#!/bin/bash
set -x

# Constants
CONTAINER_NAME="route-listener-container"
IMAGE_NAME="route-listener"

# Default interface
INTERFACE="ovs_eth0"
DEBUG=""
VERBOSE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -i|--interface)
      INTERFACE="$2"
      shift 2
      ;;
    --debug)
      DEBUG="--debug"
      shift
      ;;
    --verbose)
      VERBOSE="--verbose"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [-i|--interface <interface>] [--debug] [--verbose]"
      exit 1
      ;;
  esac
done

# Function to clean up on exit
cleanup() {
    echo "🛑 Cleaning up..."
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        docker stop $CONTAINER_NAME > /dev/null 2>&1
    fi
    exit 0
}

# Set up trap for cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Build the Docker image
echo "🏗️  Building Docker image... "
docker build -t $IMAGE_NAME .

# Check if container is already running and stop it
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "🛑 Stopping existing container..."
    docker stop $CONTAINER_NAME
fi

# Run the container with required capabilities
echo "🚀 Starting container with name: $CONTAINER_NAME on interface: $INTERFACE..."
docker run --rm \
  --name $CONTAINER_NAME \
  --network=host \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --cap-add=NET_BROADCAST \
  --cap-add=SYS_ADMIN \
  -it \
  $IMAGE_NAME /bin/sh bin/start.sh -i "$INTERFACE" $DEBUG $VERBOSE

# If we get here, the container has exited
echo "📋 Container has exited." 