# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os

# 3p
import mock

# project
from tests.checks.common import AgentCheckTest, Fixtures

metrics = [
    'system.nfs.ops',
    'system.nfs.rpc_bklog',
    'system.nfs.read_per_op',
    'system.nfs.read.ops',
    'system.nfs.read_per_s',
    'system.nfs.read.retrans',
    'system.nfs.read.retrans.pct',
    'system.nfs.read.rtt',
    'system.nfs.read.exe',
    'system.nfs.write_per_op',
    'system.nfs.write.ops',
    'system.nfs.write_per_s',
    'system.nfs.write.retrans',
    'system.nfs.write.retrans.pct',
    'system.nfs.write.rtt',
    'system.nfs.write.exe',
]

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'ci')

def mock_mounts():
    mounts = Fixtures.read_file('mounts', sdk_dir=FIXTURE_DIR)
    return mounts.splitlines()

class TestNfsstat(AgentCheckTest):
    """Basic Test for nfsstat integration."""
    CHECK_NAME = 'nfsstat'

    CONFIG = {
        'init_config': {
            'nfsiostat_path': '/opt/datadog-agent/embedded/sbin/nfsiostat'
        },
        'instances': [{}]
    }

    def setUp(self):
        """
        Load the check so its ready for patching.
        """
        self.load_check(self.CONFIG)

    @mock.patch('datadog_checks.nfsstat.nfsstat.get_subprocess_output',
                return_value=(Fixtures.read_file('nfsiostat', sdk_dir=FIXTURE_DIR), "", 0))
    def test_check(self, nfsiostat_mocks):
        """
        Testing Nfsstat check.
        """
        self.run_check(self.CONFIG)

        nfs_server_tag = 'nfs_server:192.168.34.1'
        nfs_export_tag = 'nfs_export:/exports/nfs/datadog/{0}'
        nfs_mount_tag = 'nfs_mount:/mnt/datadog/{0}'

        folder_names = ['one', 'two', 'three', 'four', 'five']

        # self.assertTrue(False)

        for metric in metrics:
            for folder in folder_names:
                tags = []
                tags.append(nfs_server_tag)
                tags.append(nfs_export_tag.format(folder))
                tags.append(nfs_mount_tag.format(folder))
                self.assertMetric(metric, tags=tags)

        self.coverage_report()
