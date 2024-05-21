#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y software-properties-common build-essential git curl wget

source /etc/os-release
echo "deb http://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /" | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
curl -L "http://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/Release.key" | sudo apt-key add -
sudo apt update
sudo apt -y install podman

sudo useradd -s /bin/bash -d /opt/stack -m stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
sudo -u stack bash << EOF
cd /opt/stack
git clone https://opendev.org/openstack/devstack --branch stable/2023.1
cd devstack
cp /tmp/local.conf .
./stack.sh
EOF