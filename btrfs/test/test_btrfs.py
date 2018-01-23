# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

@attr('unix')
class TestBtrfs(AgentCheckTest):
    """Basic Test for btrfs integration."""
    CHECK_NAME = 'btrfs'

    def mock_get_usage(self, mountpoint):
        return [(1, 9672065024, 9093722112), (34, 33554432, 16384), (36, 805306368, 544276480), (562949953421312, 184549376, 0)]

    def test_check(self):
        """
        Testing Btrfs check.
        """
        self.run_check({}, mocks={
            'get_usage': self.mock_get_usage
        })

        self.assertMetric('system.disk.btrfs.total', at_least=0)
        self.assertMetric('system.disk.btrfs.used', at_least=0)
        self.assertMetric('system.disk.btrfs.free', at_least=0)
        self.assertMetric('system.disk.btrfs.usage', at_least=0)

        self.coverage_report()
