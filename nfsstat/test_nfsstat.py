# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest

metrics = [
    'nfsstat.blocks_read_per_sec',
    'nfsstat.blocks_written_per_sec',
    'nfsstat.blocks_read_direct_per_sec',
    'nfsstat.blocks_written_direct_per_sec',
    'nfsstat.blocks_read_from_server_per_sec',
    'nfsstat.blocks_written_to_server_per_sec',
    'nfsstat.ops_per_sec',
    'nfsstat.read_ops_per_sec',
    'nfsstat.write_ops_per_sec',
]

@attr(requires='nfsstat')
class TestNfsstat(AgentCheckTest):
    """Basic Test for nfsstat integration."""
    CHECK_NAME = 'nfsstat'

    def test_check(self):
        """
        Testing Nfsstat check.
        """
        config = {
            'instances': [{}]
        }
        self.run_check(config)

        for metric in metrics:
            self.assertMetric(metric)

        self.coverage_report()
