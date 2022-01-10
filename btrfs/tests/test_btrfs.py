# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import collections

import mock

# project
import datadog_checks.btrfs

btrfs_check = datadog_checks.btrfs.BTRFS('btrfs', {}, [{}])


def mock_get_usage():

    return [
        (1, 9672065024, 9093722112),
        (34, 33554432, 16384),
        (36, 805306368, 544276480),
        (562949953421312, 184549376, 0),
    ]


# Just return a single device so the psutil portion of the check doesn't fail
# The real data to check against is in mock_get_usage.
def get_mock_devices():

    device_tuple = collections.namedtuple('device_tuple', 'device mountpoint fstype opts')

    return [device_tuple(device='/dev/disk1', mountpoint='/', fstype='btrfs', opts='local,multilabel')]


@mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions', return_value=get_mock_devices())
@mock.patch('datadog_checks.btrfs.btrfs.BTRFS.get_usage', return_value=mock_get_usage())
def test_check(mock_get_usage, mock_device_list, aggregator, dd_run_check):
    """
    Testing Btrfs check.
    """
    with mock.patch.object(btrfs_check, 'get_unallocated_space', return_value=None):
        dd_run_check(btrfs_check)

    aggregator.assert_metric('system.disk.btrfs.unallocated', count=0)

    aggregator.reset()
    with mock.patch.object(btrfs_check, 'get_unallocated_space', return_value=0):
        btrfs_check.check({})

    aggregator.assert_metric('system.disk.btrfs.total', count=4)
    aggregator.assert_metric('system.disk.btrfs.used', count=4)
    aggregator.assert_metric('system.disk.btrfs.free', count=4)
    aggregator.assert_metric('system.disk.btrfs.usage', count=4)
    aggregator.assert_metric('system.disk.btrfs.unallocated', count=1)

    aggregator.assert_all_metrics_covered()


class MockStruct:
    def __init__(self, side_effects, size):
        self.counter = 0
        self.side_effects = side_effects
        self.size = size

    def unpack(self, data):
        ret = self.side_effects[self.counter]
        self.counter += 1
        return ret

    def unpack_from(self, data, _):
        return self.unpack(data)

    def pack_into(self, *v):
        pass


@mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions', return_value=get_mock_devices())
@mock.patch('datadog_checks.btrfs.btrfs.fcntl.ioctl')
def test_get_usage(mock_ioctl, mock_device_list):
    datadog_checks.btrfs.btrfs.TWO_LONGS_STRUCT = MockStruct([(0, 4), (0, 4)], 2)
    datadog_checks.btrfs.btrfs.THREE_LONGS_STRUCT = MockStruct(mock_get_usage(), 2)

    usage = btrfs_check.get_usage('/')

    assert usage == mock_get_usage()
