# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .common import DEFAULT_DEVICE_NAME, DEFAULT_FILE_SYSTEM, DEFAULT_MOUNT_POINT, HERE


def mock_df_output(fname):
    """
    Load fixtures from tests/fixtures/ folder and return a tuple matching the
    return value of `get_subprocess_output`
    """
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return f.read(), '', ''


class MockPart(object):
    def __init__(
        self, device=DEFAULT_DEVICE_NAME, fstype=DEFAULT_FILE_SYSTEM, mountpoint=DEFAULT_MOUNT_POINT, opts='ro'
    ):
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
