#!/bin/bash
# Ensure the Docker daemon is running, starting it if necessary.
# Works on Linux, macOS, and Windows (Git Bash) runners.

set -euo pipefail

start_docker() {
  case "$RUNNER_OS" in
    Linux)
      sudo systemctl start docker
      ;;
    macOS)
      open -a Docker
      ;;
    Windows)
      powershell -Command "Start-Service docker"
      ;;
    *)
      echo "::error::Unsupported platform: $RUNNER_OS"
      exit 1
      ;;
  esac
}

if docker info > /dev/null 2>&1; then
  echo "Docker is running."
  exit 0
fi

echo "Docker is not running. Attempting to start..."
start_docker

# macOS Docker Desktop takes longer to initialise
if [ "$RUNNER_OS" == "macOS" ]; then
  retries=30
else
  retries=15
fi

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
