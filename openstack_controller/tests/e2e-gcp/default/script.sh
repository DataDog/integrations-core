#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo useradd -s /bin/bash -d /opt/stack -m stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
sudo -u stack bash << EOF
cd /opt/stack
git clone https://opendev.org/openstack/devstack --branch stable/2023.1
cd devstack
echo "[[local|localrc]]" > local.conf
echo "DATABASE_PASSWORD=password" >> local.conf
echo "ADMIN_PASSWORD=password" >> local.conf
echo "SERVICE_PASSWORD=password" >> local.conf
echo "SERVICE_TOKEN=password" >> local.conf
echo "RABBIT_PASSWORD=password" >> local.conf
echo "# Enable Logging" >> local.conf
echo "LOGFILE=/opt/stack/logs/stack.sh.log" >> local.conf
echo "VERBOSE=True" >> local.conf
echo "LOG_COLOR=True" >> local.conf
echo "#Enable heat services" >> local.conf
echo "enable_service h-eng h-api h-api-cfn h-api-cw" >> local.conf
echo "#Enable heat plugin" >> local.conf
echo "enable_plugin heat https://opendev.org/openstack/heat stable/2023.1" >> local.conf
./stack.sh
EOF