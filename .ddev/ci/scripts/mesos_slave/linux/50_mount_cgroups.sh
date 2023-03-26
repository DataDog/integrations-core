#!/bin/bash

set -ex

docker info

sudo apt update
sudo apt -y install cgroup-tools

sudo mkdir /sys/fs/cgroup/systemd
sudo mount -t cgroup -o none,name=systemd cgroup /sys/fs/cgroup/systemd

set +ex
