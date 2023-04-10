#!/opt/homebrew/bin/bash

./create_mocks.sh "agent-integrations-openstack-default"
./create_mocks.sh "agent-integrations-openstack-default" default latest
./create_mocks.sh "agent-integrations-openstack-default" latest default
./create_mocks.sh "agent-integrations-openstack-default" latest latest

./create_mocks.sh "agent-integrations-openstack-ironic"
./create_mocks.sh "agent-integrations-openstack-ironic" default latest
./create_mocks.sh "agent-integrations-openstack-ironic" latest default
./create_mocks.sh "agent-integrations-openstack-ironic" latest latest

./create_mocks.sh "agent-integrations-openstack-octavia"
./create_mocks.sh "agent-integrations-openstack-octavia" default latest
./create_mocks.sh "agent-integrations-openstack-octavia" latest default
./create_mocks.sh "agent-integrations-openstack-octavia" latest latest