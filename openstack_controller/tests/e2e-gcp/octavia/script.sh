#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo useradd -s /bin/bash -d /opt/stack -m stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
cd /opt/stack
sudo git clone https://opendev.org/openstack/devstack
cd devstack
sudo git checkout stable/zed
cat <<EOF | sudo tee -a local.conf
# Sample ``local.conf`` that builds a devstack with neutron LBaaS Version 2

# NOTE: Copy this file to the root DevStack directory for it to work properly.

# ``local.conf`` is a user-maintained settings file that is sourced from ``stackrc``.
# This gives it the ability to override any variables set in ``stackrc``.
# Also, most of the settings in ``stack.sh`` are written to only be set if no
# value has already been set; this lets ``local.conf`` effectively override the
# default values.

# The ``localrc`` section replaces the old ``localrc`` configuration file.
# Note that if ``localrc`` is present it will be used in favor of this section.

[[local|localrc]]
# ===== BEGIN localrc =====
DATABASE_PASSWORD=password
ADMIN_PASSWORD=password
SERVICE_PASSWORD=password
SERVICE_TOKEN=password
RABBIT_PASSWORD=password
# Optional settings:
# OCTAVIA_AMP_BASE_OS=centos
# OCTAVIA_AMP_DISTRIBUTION_RELEASE_ID=9-stream
# OCTAVIA_AMP_IMAGE_SIZE=3
# OCTAVIA_LB_TOPOLOGY=ACTIVE_STANDBY
# OCTAVIA_ENABLE_AMPHORAV2_JOBBOARD=True
# LIBS_FROM_GIT+=octavia-lib,
# Enable Logging
LOGFILE=/opt/stack/logs/stack.sh.log
VERBOSE=True
LOG_COLOR=True
enable_service rabbit
enable_plugin neutron https://opendev.org/openstack/neutron stable/zed
# Octavia supports using QoS policies on the VIP port:
enable_service q-qos
enable_service placement-api placement-client
# Octavia services
enable_plugin octavia https://opendev.org/openstack/octavia stable/zed
enable_plugin octavia-dashboard https://opendev.org/openstack/octavia-dashboard stable/zed
enable_plugin ovn-octavia-provider https://opendev.org/openstack/ovn-octavia-provider stable/zed
#enable_plugin octavia-tempest-plugin https://opendev.org/openstack/octavia-tempest-plugin master
enable_service octavia o-api o-cw o-hm o-hk o-da
# If you are enabling barbican for TLS offload in Octavia, include it here.
# enable_plugin barbican https://opendev.org/openstack/barbican stable/zed
# enable_service barbican
# Cinder (optional)
disable_service c-api c-vol c-sch
# Tempest
#enable_service tempest
# ===== END localrc =====
EOF
sudo chown stack:stack /opt/stack/devstack -R
sudo -u stack -H ./stack.sh