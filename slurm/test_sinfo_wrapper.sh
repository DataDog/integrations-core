#!/bin/bash
# test_sinfo_wrapper.sh - Simple test script to see what parameters are passed

echo "=== Test sinfo wrapper script ==="
echo "Script name: $0"
echo "Number of arguments: $#"
echo "All arguments: $@"
echo "Arguments as array:"
for i in "$@"; do
    echo "  '$i'"
done
echo "=== End of test ===" 