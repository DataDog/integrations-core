#!/bin/bash
set -e

ORIGINAL_DIR=$(pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV="py3.13-2"

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
            echo "  -e, --env ENV    ddev environment to use (default: py3.13-2)"
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

cleanup() {
    echo ""
    echo "Cleaning up..."
    cd "$SCRIPT_DIR"
    hatch run lab:stop -e "$ENV" || true
    cd "$ORIGINAL_DIR"
    exit 0
}

# `lab:generate` runs through `hatch`, which traps SIGINT itself, so we
# install our own EXIT trap to make sure `lab:stop` always runs even on Ctrl+C.
trap cleanup EXIT

cd "$SCRIPT_DIR"
hatch run lab:start -e "$ENV"

echo "Starting traffic (Ctrl+C to stop)..."
hatch run lab:generate
