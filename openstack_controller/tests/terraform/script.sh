#!/bin/bash
sudo useradd -s /bin/bash -d /opt/stack -m stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
cd /opt/stack
sudo git clone https://opendev.org/openstack/devstack
cd devstack
IP=$(ip route get 8.8.8.8 | awk -F"src " 'NR==1{split($2,a," ");print a[1]}')
IP_PREFIX=$(echo $IP | cut -d. -f 1,2,3)
cat <<EOF | sudo tee -a local.conf
[[local|localrc]]
FIXED_RANGE=10.4.128.0/20
FLOATING_RANGE=$IP_PREFIX.128/25
LOGFILE=/opt/stack/logs/stack.sh.log
ADMIN_PASSWORD=labstack
DATABASE_PASSWORD=supersecret
RABBIT_PASSWORD=supersecret
SERVICE_PASSWORD=supersecret
EOF
sudo chown stack:stack /opt/stack/devstack -R
sudo -u stack -H ./stack.sh
