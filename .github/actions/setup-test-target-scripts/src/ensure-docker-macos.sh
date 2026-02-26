#!/bin/bash
# Ensure Docker daemon is running on macOS runners

set -euo pipefail

if docker info > /dev/null 2>&1; then
  echo "Docker is running."
  exit 0
fi

echo "Docker is not running. Attempting to start..."
open -a Docker

# Wait for Docker to be ready
retries=30
while [ $retries -gt 0 ]; do
  if docker info > /dev/null 2>&1; then
    echo "Docker is running."
    exit 0
  fi
  echo "Waiting for Docker to start... ($retries retries left)"
  sleep 2
  retries=$((retries - 1))
done

echo "::error::Docker failed to start after retries."
exit 1
