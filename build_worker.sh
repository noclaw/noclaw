#!/bin/bash
# Build script for worker container with Claude SDK

set -e

echo "Building NoClaw Worker Container"
echo "================================="
echo ""

# Detect container runtime
if command -v docker &> /dev/null; then
    RUNTIME="docker"
elif command -v podman &> /dev/null; then
    RUNTIME="podman"
else
    echo "Error: No container runtime found. Install Docker or Podman."
    exit 1
fi

echo "Using runtime: $RUNTIME"

# Build the worker image
echo "Building worker image with Claude SDK..."
$RUNTIME build -f worker/Dockerfile -t noclaw-worker:latest .

echo ""
echo "Build complete!"
echo ""
echo "Next steps:"
echo "1. Set your Claude OAuth token:"
echo ""
echo "2. Run the assistant:"
echo "   python run_assistant.py"
echo ""
echo "The worker will use the Claude SDK to process requests."