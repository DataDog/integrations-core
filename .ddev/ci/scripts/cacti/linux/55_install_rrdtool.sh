#!/bin/bash

set -ex

sudo apt-get update
sudo apt-get install -y --no-install-recommends librrd-dev rrdtool

set +ex
