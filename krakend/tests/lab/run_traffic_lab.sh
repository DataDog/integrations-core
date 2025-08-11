#!/bin/bash

set -e

ORIGINAL_DIR=$(pwd)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV="py3.12-2.10"

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-e|--env ENV]"
            echo ""
            echo "Options:"
            echo "  -e, --env ENV    Environment to use (default: py3.12-2.10)"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Cleaning up..."

    cd "$SCRIPT_DIR"
    hatch run lab:stop -e "$ENV"
    cd "$ORIGINAL_DIR"
    exit 0
}

# Set trap to ensure cleanup runs on script exit (including Ctrl+C)
# This is needed because running the scripts using click within a click application (hatch)
# Makes it very hard to avoid a SIGINT signal propagating and kill the execution of the stop command
# This is a workaround to ensure the cleanup function is called on exit
trap cleanup EXIT

echo "Changing to lab directory: $SCRIPT_DIR"
cd "$SCRIPT_DIR"

hatch run lab:start -e "$ENV"

echo "Starting traffic generation (press Ctrl+C to stop)..."
hatch run lab:generate
