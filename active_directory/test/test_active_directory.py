# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import copy

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


INSTANCE = {
}

INSTANCE_METRICS = [
    'active_directory.ldap.client_sessions',
    'active_directory.ldap.bind_time',
]

@attr('windows')
@attr(requires='active_directory')
class ActiveDirectoryCheckTest(AgentCheckTest):
    CHECK_NAME = 'active_directory'

    def test_basic_check(self):
        instance = copy.deepcopy(INSTANCE)
        self.run_check({'instances': [instance]})

        for metric in INSTANCE_METRICS:
            self.assertMetric(metric, tags=None, count=1)

        self.coverage_report()
