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
echo "# Credentials" >> local.conf
echo "ADMIN_PASSWORD=password" >> local.conf
echo "DATABASE_PASSWORD=password" >> local.conf
echo "RABBIT_PASSWORD=password" >> local.conf
echo "SERVICE_PASSWORD=password" >> local.conf
echo "SERVICE_TOKEN=password" >> local.conf
echo "" >> local.conf
echo "# Set glance's default limit to be baremetal image friendly" >> local.conf
echo "GLANCE_LIMIT_IMAGE_SIZE_TOTAL=5000" >> local.conf
echo "" >> local.conf
echo "# Configure ironic from ironic devstack plugin." >> local.conf
echo "enable_plugin ironic https://opendev.org/openstack/ironic stable/2023.1" >> local.conf
echo "enable_plugin ironic-ui https://github.com/openstack/ironic-ui stable/2023.1" >> local.conf
echo "" >> local.conf
echo "# Create 3 virtual machines to pose as Ironic's baremetal nodes." >> local.conf
echo "IRONIC_VM_COUNT=3" >> local.conf
echo "IRONIC_BAREMETAL_BASIC_OPS=True" >> local.conf
echo "DEFAULT_INSTANCE_TYPE=baremetal" >> local.conf
echo "" >> local.conf
echo "# Enable services" >> local.conf
echo "enable_service horizon" >> local.conf
echo "enable_service g-api" >> local.conf
echo "enable_service key" >> local.conf
echo "enable_service memory_tracker" >> local.conf
echo "enable_service mysql" >> local.conf
echo "enable_service q-agt" >> local.conf
echo "enable_service q-dhcp" >> local.conf
echo "enable_service q-l3" >> local.conf
echo "enable_service q-meta" >> local.conf
echo "enable_service q-metering" >> local.conf
echo "enable_service q-svc" >> local.conf
echo "enable_service rabbit" >> local.conf
echo "" >> local.conf
echo "# Enable Ironic API and Ironic Conductor" >> local.conf
echo "enable_service ironic" >> local.conf
echo "enable_service ir-api" >> local.conf
echo "enable_service ir-cond" >> local.conf
echo "" >> local.conf
echo "# Disable nova novnc service, ironic does not support it anyway." >> local.conf
echo "disable_service n-novnc" >> local.conf
echo "" >> local.conf
echo "# Disable Cinder" >> local.conf
echo "disable_service cinder c-sch c-api c-vol" >> local.conf
echo "" >> local.conf
echo "# Disable Tempest" >> local.conf
echo "disable_service tempest" >> local.conf
echo "" >> local.conf
echo "IRONIC_RPC_TRANSPORT=json-rpc" >> local.conf
echo "IRONIC_RAMDISK_TYPE=tinyipa" >> local.conf
echo "IRONIC_RAMDISK_TYPE=tinyipa" >> local.conf
echo "" >> local.conf
echo "# Enable additional hardware types, if needed." >> local.conf
echo "IRONIC_ENABLED_HARDWARE_TYPES=ipmi,fake-hardware" >> local.conf
echo "# Don't forget that many hardware types require enabling of additional" >> local.conf
echo "# interfaces, most often power and management:" >> local.conf
echo "IRONIC_ENABLED_MANAGEMENT_INTERFACES=ipmitool,fake" >> local.conf
echo "IRONIC_ENABLED_POWER_INTERFACES=ipmitool,fake" >> local.conf
echo "IRONIC_DEFAULT_DEPLOY_INTERFACE=direct" >> local.conf
echo "" >> local.conf
echo "# Change this to alter the default driver for nodes created by devstack." >> local.conf
echo "# This driver should be in the enabled list above." >> local.conf
echo "IRONIC_DEPLOY_DRIVER="ipmi"" >> local.conf
echo "" >> local.conf
echo "# The parameters below represent the minimum possible values to create" >> local.conf
echo "# functional nodes." >> local.conf
echo "IRONIC_VM_SPECS_RAM=1024" >> local.conf
echo "IRONIC_VM_SPECS_DISK=3" >> local.conf
echo "" >> local.conf
echo "# Size of the ephemeral partition in GB. Use 0 for no ephemeral partition." >> local.conf
echo "IRONIC_VM_EPHEMERAL_DISK=0" >> local.conf
echo "" >> local.conf
echo "# To build your own IPA ramdisk from source, set this to True" >> local.conf
echo "IRONIC_BUILD_DEPLOY_RAMDISK=False" >> local.conf
echo "" >> local.conf
echo "INSTALL_TEMPEST=False" >> local.conf
echo "VIRT_DRIVER=ironic" >> local.conf
echo "" >> local.conf
echo "# By default, DevStack creates a 10.0.0.0/24 network for instances." >> local.conf
echo "# If this overlaps with the hosts network, you may adjust with the" >> local.conf
echo "# following." >> local.conf
echo "IP_VERSION=4" >> local.conf
echo "FIXED_RANGE=10.1.0.0/20" >> local.conf
echo "IPV4_ADDRS_SAFE_TO_USE=10.1.0.0/20" >> local.conf
echo "NETWORK_GATEWAY=10.1.0.1" >> local.conf
echo "" >> local.conf
echo "Q_AGENT=openvswitch" >> local.conf
echo "Q_ML2_PLUGIN_MECHANISM_DRIVERS=openvswitch" >> local.conf
echo "Q_ML2_TENANT_NETWORK_TYPE=vxlan" >> local.conf
echo "" >> local.conf
echo "# Log all output to files" >> local.conf
echo "LOGFILE=/opt/stack/devstack.log" >> local.conf
echo "LOGDIR=/opt/stack/logs" >> local.conf
echo "IRONIC_VM_LOG_DIR=/opt/stack/ironic-bm-logs" >> local.conf
./stack.sh
EOF
