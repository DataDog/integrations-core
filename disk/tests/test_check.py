# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys
import os

import pytest
import mock

from datadog_checks.disk import Disk

# Skip the whole tests module on Windows
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='tests for linux only')

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DEVICE_NAME = '/dev/sda1'
DISK_GAUGES = [
    'system.disk.free',
    'system.disk.in_use',
    'system.disk.total',
    'system.disk.used',
]
DISK_RATES = [
    'system.disk.write_time_pct',
    'system.disk.read_time_pct',
]
INODE_GAUGES = [
    'system.fs.inodes.total',
    'system.fs.inodes.used',
    'system.fs.inodes.free',
    'system.fs.inodes.in_use'
]
GAUGES_VALUES = {
    'system.disk.total': 5,
    'system.disk.used': 4,
    'system.disk.free': 1,
    'system.disk.in_use': .80,
    'system.fs.inodes.total': 10,
    'system.fs.inodes.used': 1,
    'system.fs.inodes.free': 9,
    'system.fs.inodes.in_use': .10
}
RATES_VALUES = {
    'system.disk.write_time_pct': 9.0,
    'system.disk.read_time_pct': 5.0,
}


class MockPart(object):
    def __init__(self, device=DEFAULT_DEVICE_NAME, fstype='ext4', mountpoint='/', opts='ro'):
        self.device = device
        self.fstype = fstype
        self.mountpoint = mountpoint
        self.opts = opts


class MockDiskMetrics(object):
    total = 5 * 1024
    used = 4 * 1024
    free = 1 * 1024
    percent = 80
    read_time = 50
    write_time = 90


class MockDiskIOMetrics(dict):
    def __init__(self, device=DEFAULT_DEVICE_NAME):
        super(MockDiskIOMetrics, self).__init__()
        self[device] = MockDiskMetrics()


class MockInodesMetrics(object):
    f_files = 10
    f_ffree = 9


class MockIoCountersMetrics(object):
    read_time = 15
    write_time = 25


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator

@pytest.fixture(scope="module")
def psutil_mocks():
    p1 = mock.patch('psutil.disk_partitions', return_value=[MockPart()],
                    __name__="disk_partitions")
    p2 = mock.patch('psutil.disk_usage', return_value=MockDiskMetrics(),
                    __name__="disk_usage")
    p3 = mock.patch('os.statvfs', return_value=MockInodesMetrics(),
                    __name__="statvfs")
    p4 = mock.patch('psutil.disk_io_counters', return_value=MockDiskIOMetrics())

    yield p1.start(), p2.start(), p3.start(), p4.start()

    p1.stop()
    p2.stop()
    p3.stop()
    p4.stop()

def test_bad_config():
    """
    Check creation will fail if more than one `instance` is passed to the
    constructor
    """
    with pytest.raises(Exception):
        Disk('disk', None, {}, [{}, {}])
