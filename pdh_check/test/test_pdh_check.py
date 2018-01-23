# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import copy

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


INSTANCE = {
    'countersetname': 'System',
    'metrics': [
        ['File Read Operations/sec', 'pdh.system.file_read_per_sec', 'gauge'],
        ['File Write Bytes/sec', 'pdh.system.file_write_bytes_sec', 'gauge'],
    ]
}

INSTANCE_METRICS = [
    'pdh.system.file_read_per_sec',
    'pdh.system.file_write_bytes_sec',
]

@attr('windows')
@attr(requires='pdh_check')
class PDHCheckTest(AgentCheckTest):
    CHECK_NAME = 'pdh_check'

    def test_basic_check(self):
        instance = copy.deepcopy(INSTANCE)
        self.run_check({'instances': [instance]})

        for metric in INSTANCE_METRICS:
            self.assertMetric(metric, tags=None, count=1)

        self.coverage_report()
