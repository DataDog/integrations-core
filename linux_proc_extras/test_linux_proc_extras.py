# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os

# 3p
from mock import mock_open, patch
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest, Fixtures

@attr('unix')
class TestCheckLinuxProcExtras(AgentCheckTest):
    CHECK_NAME = 'linux_proc_extras'

    INODE_GAUGES = [
        'system.inodes.total',
        'system.inodes.used'
    ]

    PROC_COUNTS = [
        'system.linux.context_switches',
        'system.linux.processes_created',
        'system.linux.interrupts'
    ]

    ENTROPY_GAUGES = [
        'system.entropy.available'
    ]

    PROCESS_STATS_GAUGES = [
        'system.processes.states',
        'system.processes.priorities'
    ]

    # Really a basic check to see if all metrics are there
    def test_check(self):

        self.load_check({'instances': []})

        self.check.proc_path_map = {
            "inode_info": "/proc/sys/fs/inode-nr",
            "stat_info": "/proc/stat",
            "entropy_info": "/proc/sys/kernel/random/entropy_avail",
        }
        self.check.tags = []

        ci_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ci")
        m = mock_open(read_data=Fixtures.read_file('entropy_avail', sdk_dir=ci_dir))
        with patch('__builtin__.open', m):
            self.check.get_entropy_info()

        m = mock_open(read_data=Fixtures.read_file('inode-nr', sdk_dir=ci_dir))
        with patch('__builtin__.open', m):
            self.check.get_inode_info()

        m = mock_open(read_data=Fixtures.read_file('proc-stat', sdk_dir=ci_dir))
        with patch('__builtin__.open', m):
            self.check.get_stat_info()
            self.check.get_stat_info()

        with patch('linux_proc_extras.get_subprocess_output', return_value=
                   (Fixtures.read_file('process_stats', sdk_dir=ci_dir), "", 0)):
            self.check.get_process_states()

        self.metrics = self.check.get_metrics()
        self.events = self.check.get_events()
        self.service_checks = self.check.get_service_checks()
        self.service_metadata = []
        self.warnings = self.check.get_warnings()

        self.check.log.info(self.metrics)

        # Assert metrics
        for metric in self.PROC_COUNTS + self.INODE_GAUGES + self.ENTROPY_GAUGES + self.PROCESS_STATS_GAUGES:
            self.assertMetric(metric)

        self.coverage_report()
