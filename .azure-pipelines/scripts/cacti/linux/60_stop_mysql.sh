#!/bin/bash

set -ex

sudo systemctl status mysql || true
sudo systemctl stop mysql
sudo systemctl status mysql || true

set +ex
