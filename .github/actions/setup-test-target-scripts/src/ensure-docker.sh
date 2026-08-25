#!/bin/bash
# Ensure the Docker daemon is running, starting it if necessary.
# Works on Linux and Windows (Git Bash) runners. On macOS, Docker is not
# available on GitHub-hosted runners so the check is skipped.

set -euo pipefail

start_docker() {
  case "$RUNNER_OS" in
    Linux)
      sudo systemctl start docker
      ;;
    Windows)
      powershell -Command "Start-Service docker"
      ;;
  esac
}

# Docker is not available on GitHub-hosted macOS runners:
# - https://github.com/actions/runner-images/blob/main/images/macos/macos-14-arm64-Readme.md
# - https://github.com/actions/runner-images/blob/main/images/macos/macos-14-Readme.md
# - https://github.com/actions/runner/issues/1456
if [ "$RUNNER_OS" == "macOS" ]; then
  echo "::warning::Docker is not available on GitHub-hosted macOS runners. Tests that require Docker will likely fail."
  exit 0
fi

if docker info > /dev/null 2>&1; then
  echo "Docker is running."
  exit 0
fi

echo "Docker is not running. Attempting to start..."
start_docker

retries=15
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
