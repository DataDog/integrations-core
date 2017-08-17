# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

logging.basicConfig()

"""
Uses Oracle instance running in VM from:
https://atlas.hashicorp.com/woznial/boxes/centos-6.3-oracle-xe

Include following line in your Vagrantfile:

config.vm.network "forwarded_port", guest: 1521, host: 8521

Using the "system" user as permission granting not available
for default "system" user

Install oracle instant client in /opt/oracle

Set up Oracle instant client:
http://jasonstitt.com/cx_oracle_on_os_x

Set:
export ORACLE_HOME=/opt/oracle/instantclient_12_1/
export DYLD_LIBRARY_PATH="$ORACLE_HOME:$DYLD_LIBRARY_PATH"
"""

CONFIG = {
    'init_config': {},
    'instances': [{
        'server': 'localhost:1521',
        'user': 'system',
        'password': 'oracle',
        'service_name': 'xe',
    }]
}

@attr(requires='oracle')
class TestOracle(AgentCheckTest):
    """Basic Test for oracle integration."""
    CHECK_NAME = 'oracle'

    def testOracle(self):
        self.run_check_twice(CONFIG)
        self.coverage_report()
