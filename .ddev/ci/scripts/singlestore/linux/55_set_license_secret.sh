#!/bin/bash
set -euo pipefail

set +x

echo "SINGLESTORE_LICENSE=$SINGLESTORE_LICENSE" >> "${GITHUB_ENV:-/tmp/gh-output}"

set -x
