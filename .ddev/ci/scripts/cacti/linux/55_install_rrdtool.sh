#!/bin/bash
# AI-7430 validation: throwaway change, PR will be closed unmerged.

set -ex

sudo apt-get update
sudo apt-get install -y --no-install-recommends librrd-dev rrdtool

set +ex
