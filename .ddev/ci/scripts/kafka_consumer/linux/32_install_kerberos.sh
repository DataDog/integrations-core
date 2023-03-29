#!/bin/bash

set -ex

sudo apt-get update
sudo apt install build-essential
sudo apt-get install -y --no-install-recommends libkrb5-dev

set +ex
