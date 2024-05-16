#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo useradd -s /bin/bash -d /opt/stack -m stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
sudo -u stack bash << EOF
cd /opt/stack
git clone https://opendev.org/openstack/devstack --branch stable/2023.1
cd devstack
echo "sudo git checkout stable/2023.1" > local.conf
echo "cat <<EOF | sudo tee -a local.conf" >> local.conf
echo "# Sample ``local.conf`` that builds a devstack with neutron LBaaS Version 2" >> local.conf
echo "" >> local.conf
echo "# NOTE: Copy this file to the root DevStack directory for it to work properly." >> local.conf
echo "" >> local.conf
echo "# ``local.conf`` is a user-maintained settings file that is sourced from ``stackrc``." >> local.conf
echo "# This gives it the ability to override any variables set in ``stackrc``." >> local.conf
echo "# Also, most of the settings in ``stack.sh`` are written to only be set if no" >> local.conf
echo "# value has already been set; this lets ``local.conf`` effectively override the" >> local.conf
echo "# default values." >> local.conf
echo "" >> local.conf
echo "# The ``localrc`` section replaces the old ``localrc`` configuration file." >> local.conf
echo "# Note that if ``localrc`` is present it will be used in favor of this section." >> local.conf
echo "" >> local.conf
echo "[[local|localrc]]" >> local.conf
echo "# ===== BEGIN localrc =====" >> local.conf
echo "DATABASE_PASSWORD=password" >> local.conf
echo "ADMIN_PASSWORD=password" >> local.conf
echo "SERVICE_PASSWORD=password" >> local.conf
echo "SERVICE_TOKEN=password" >> local.conf
echo "RABBIT_PASSWORD=password" >> local.conf
echo "# Optional settings:" >> local.conf
echo "# OCTAVIA_AMP_BASE_OS=centos" >> local.conf
echo "# OCTAVIA_AMP_DISTRIBUTION_RELEASE_ID=9-stream" >> local.conf
echo "# OCTAVIA_AMP_IMAGE_SIZE=3" >> local.conf
echo "# OCTAVIA_LB_TOPOLOGY=ACTIVE_STANDBY" >> local.conf
echo "# OCTAVIA_ENABLE_AMPHORAV2_JOBBOARD=True" >> local.conf
echo "# LIBS_FROM_GIT+=octavia-lib," >> local.conf
echo "# Enable Logging" >> local.conf
echo "LOGFILE=/opt/stack/logs/stack.sh.log" >> local.conf
echo "VERBOSE=True" >> local.conf
echo "LOG_COLOR=True" >> local.conf
echo "enable_service rabbit" >> local.conf
echo "enable_plugin neutron https://opendev.org/openstack/neutron stable/2023.1" >> local.conf
echo "# Octavia supports using QoS policies on the VIP port:" >> local.conf
echo "enable_service q-qos" >> local.conf
echo "enable_service placement-api placement-client" >> local.conf
echo "# Octavia services" >> local.conf
echo "enable_plugin octavia https://opendev.org/openstack/octavia stable/2023.1" >> local.conf
echo "enable_plugin octavia-dashboard https://opendev.org/openstack/octavia-dashboard stable/2023.1" >> local.conf
echo "enable_plugin ovn-octavia-provider https://opendev.org/openstack/ovn-octavia-provider stable/2023.1" >> local.conf
echo "#enable_plugin octavia-tempest-plugin https://opendev.org/openstack/octavia-tempest-plugin master" >> local.conf
echo "enable_service octavia o-api o-cw o-hm o-hk o-da" >> local.conf
echo "# If you are enabling barbican for TLS offload in Octavia, include it here." >> local.conf
echo "# enable_plugin barbican https://opendev.org/openstack/barbican stable/2023.1" >> local.conf
echo "# enable_service barbican" >> local.conf
echo "# Cinder (optional)" >> local.conf
echo "disable_service c-api c-vol c-sch" >> local.conf
echo "# Tempest" >> local.conf
echo "#enable_service tempest" >> local.conf
echo "# ===== END localrc =====" >> local.conf
./stack.sh
EOF