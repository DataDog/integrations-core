#!/bin/bash
set -euo pipefail

set +x

echo "DD_GITHUB_USER=$DD_GITHUB_USER" >> "$GITHUB_ENV"
echo "DD_GITHUB_TOKEN=$DD_GITHUB_TOKEN" >> "$GITHUB_ENV"

set -x
