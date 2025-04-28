#!/bin/bash
sudo apt update
sudo apt upgrade -y # comment out this line if getting incompatible kernel warnings
sudo useradd -s /bin/bash -d /opt/stack -m stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
sudo -u stack bash << EOF
cd /opt/stack
git clone https://opendev.org/openstack/devstack --branch stable/2024.1
cd devstack
cp /tmp/local.conf .
LOGFILE=/opt/stack/logs/stack.sh.log FORCE=yes ./stack.sh
EOF