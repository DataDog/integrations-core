# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p
import requests

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest

config = {
    'instances': [{
        'report_url': 'http://localhost:1978/rpc/report'
    }]
}

METRICS = [
    'kyototycoon.threads',
    'kyototycoon.connections_per_s',
    'kyototycoon.ops.get.hits_per_s',
    'kyototycoon.ops.get.misses_per_s',
    'kyototycoon.ops.set.hits_per_s',
    'kyototycoon.ops.set.misses_per_s',
    'kyototycoon.ops.del.hits_per_s',
    'kyototycoon.ops.del.misses_per_s',
    'kyototycoon.records',
    'kyototycoon.size',
    'kyototycoon.ops.get.total_per_s',
    'kyototycoon.ops.get.total_per_s',
    'kyototycoon.ops.set.total_per_s',
    'kyototycoon.ops.set.total_per_s',
    'kyototycoon.ops.del.total_per_s',
    'kyototycoon.ops.del.total_per_s',
    # 'kyototycoon.replication.delay', # Since I am not spinning up multiple servers, this should be 0
]

@attr(requires='kyototycoon')
class TestKyototycoon(AgentCheckTest):
    """Basic Test for kyototycoon integration."""
    CHECK_NAME = 'kyototycoon'

    def setUp(self):
        dat = {
            'dddd': 'dddd'
        }
        headers = {
            'X-Kt-Mode': 'set'
        }
        for x in range(0, 100):
            requests.put('http://localhost:1978', data=dat, headers=headers)
            requests.get('http://localhost:1978')


    def test_check(self):
        """
        Testing Kyototycoon check.
        """
        self.run_check_twice(config)

        for mname in METRICS:
            self.assertMetric(mname, count=1, at_least=0)

        self.assertServiceCheck('kyototycoon.can_connect', status=AgentCheck.OK, at_least=1)

        self.coverage_report()
