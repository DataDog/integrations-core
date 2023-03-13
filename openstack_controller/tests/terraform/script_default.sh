#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo useradd -s /bin/bash -d /opt/stack -m stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
cd /opt/stack
sudo git clone https://opendev.org/openstack/devstack
cd devstack
sudo git checkout origin/stable/zed
cat <<EOF | sudo tee -a local.conf
[[local|localrc]]
DATABASE_PASSWORD=password
ADMIN_PASSWORD=password
SERVICE_PASSWORD=password
SERVICE_TOKEN=password
RABBIT_PASSWORD=password
# Enable Logging
LOGFILE=/opt/stack/logs/stack.sh.log
VERBOSE=True
LOG_COLOR=True
EOF
sudo chown stack:stack /opt/stack/devstack -R
sudo -u stack -H ./stack.sh