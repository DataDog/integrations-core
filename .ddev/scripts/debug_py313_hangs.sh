#!/bin/bash
# Debug script to help identify Python 3.13 hanging issues
# Usage: ./.ddev/scripts/debug_py313_hangs.sh [integration_name]

set -e

INTEGRATION="${1:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Python 3.13 Hang Debug Tool ==="
echo ""

# 1. Search for multiprocessing + logging patterns
echo "1. Searching for multiprocessing + logging patterns..."
echo "   (These can cause hangs in Python 3.13)"
echo ""

if [ -n "$INTEGRATION" ]; then
    SEARCH_PATH="$REPO_ROOT/$INTEGRATION"
else
    SEARCH_PATH="$REPO_ROOT"
fi

echo "Searching in: $SEARCH_PATH"
echo ""

echo "Files using multiprocessing.Queue:"
grep -r "multiprocessing.Queue" "$SEARCH_PATH" --include="*.py" 2>/dev/null || echo "  None found"
echo ""

echo "Files using QueueHandler:"
grep -r "QueueHandler\|logging.handlers.Queue" "$SEARCH_PATH" --include="*.py" 2>/dev/null || echo "  None found"
echo ""

echo "Files using multiprocessing with logging:"
grep -l "import multiprocessing" "$SEARCH_PATH" --include="*.py" -r 2>/dev/null | while read -r file; do
    if grep -q "import logging\|from logging" "$file" 2>/dev/null; then
        echo "  $file (uses both multiprocessing and logging)"
    fi
done
echo ""

# 2. Search for background threads/processes in fixtures
echo "2. Searching for fixtures with background threads/processes..."
grep -r "@pytest.fixture" "$SEARCH_PATH" --include="conftest.py" -A 20 2>/dev/null | \
    grep -E "Thread\(|Process\(|multiprocessing\.|threading\." || echo "  None found"
echo ""

# 3. Suggest tests to run
echo "3. Suggested debugging commands:"
echo ""
if [ -n "$INTEGRATION" ]; then
    echo "Run with debugging enabled:"
    echo "  DDEV_DEBUG_HANGS=1 ddev test $INTEGRATION"
    echo ""
    echo "Run specific test with timeout:"
    echo "  DDEV_DEBUG_HANGS=1 ddev test $INTEGRATION -- -k test_name --timeout=120"
    echo ""
    echo "Run with faulthandler only (no timeout):"
    echo "  DDEV_DEBUG_HANGS=1 DDEV_TEST_TIMEOUT=0 ddev test $INTEGRATION"
else
    echo "Specify an integration to get specific commands, e.g.:"
    echo "  $0 postgres"
fi
echo ""

echo "4. To capture hanging state:"
echo "   When a test hangs, run in another terminal:"
echo "   ps aux | grep python"
echo "   kill -SIGUSR1 <pid>  # This will trigger faulthandler dump"
echo ""

echo "=== End Debug Tool ==="

