# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
from nose.plugins.attrib import attr

# 3p
import mock

# project
from tests.checks.common import AgentCheckTest, Fixtures

metrics = [
    'system.nfs.read_per_sec',
    'system.nfs.writes_per_sec',
    'system.nfs.read_direct_per_sec',
    'system.nfs.writes_direct_per_sec',
    'system.nfs.read_from_server_per_sec',
    'system.nfs.written_to_server_per_sec',
    'system.nfs.ops_per_sec',
    'system.nfs.read_ops_per_sec',
    'system.nfs.write_ops_per_sec',
]

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'ci')

def mock_mounts():
    mounts = Fixtures.read_file('mounts', sdk_dir=FIXTURE_DIR)
    return mounts.splitlines()

@attr(requires='nfsstat')
class TestNfsstat(AgentCheckTest):
    """Basic Test for nfsstat integration."""
    CHECK_NAME = 'nfsstat'

    CONFIG = {
        'instances': [{}]
    }

    def setUp(self):
        """
        Load the check so its ready for patching.
        """
        self.load_check({'instances': [self.CONFIG]})

    @mock.patch('_nfsstat.get_subprocess_output',
                return_value=(Fixtures.read_file('nfsiostat-sysstat', sdk_dir=FIXTURE_DIR), "", 0))
    @mock.patch('_nfsstat.NfsStatCheck.read_mounts', return_value=(mock_mounts()))
    def test_check(self, mock_dfs, mock_mounts):
        """
        Testing Nfsstat check.
        """
        config = {
            'instances': [{}]
        }
        self.run_check(config)
        nfs_server_tag = 'nfs_server:192.168.34.1'
        nfs_export_tag = 'nfs_export:/exports/nfs/datadog/{0}'
        nfs_mount_tag = 'nfs_mount:/mnt/datadog/{0}'

        folder_names = ['one', 'two', 'three', 'four', 'five']

        for metric in metrics:
            for folder in folder_names:
                tags = []
                tags.append(nfs_server_tag)
                tags.append(nfs_export_tag.format(folder))
                tags.append(nfs_mount_tag.format(folder))
                self.assertMetric(metric, tags=tags)

        self.coverage_report()
