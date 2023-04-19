#!/opt/homebrew/bin/bash

./create_mocks.sh "agent-integrations-openstack-default" "" ""
./create_mocks.sh "agent-integrations-openstack-default" "" 1.80
./create_mocks.sh "agent-integrations-openstack-default" 2.93 ""
./create_mocks.sh "agent-integrations-openstack-default" 2.93 1.80

./create_mocks.sh "agent-integrations-openstack-ironic" "" ""
./create_mocks.sh "agent-integrations-openstack-ironic" "" 1.80
./create_mocks.sh "agent-integrations-openstack-ironic" 2.93 ""
./create_mocks.sh "agent-integrations-openstack-ironic" 2.93 1.80

./create_mocks.sh "agent-integrations-openstack-octavia" "" ""
./create_mocks.sh "agent-integrations-openstack-octavia" "" 1.80
./create_mocks.sh "agent-integrations-openstack-octavia" 2.93 ""
./create_mocks.sh "agent-integrations-openstack-octavia" 2.93 1.80

./create_mocks.sh "agent-integrations-openstack-octavia"
