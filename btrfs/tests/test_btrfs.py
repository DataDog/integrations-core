# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import collections
import mock
import pytest

# project
from datadog_checks.btrfs import BTRFS

btrfs_check = BTRFS('btrfs', {}, {})


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def mock_get_usage():

    return [
        (1, 9672065024, 9093722112),
        (34, 33554432, 16384),
        (36, 805306368, 544276480),
        (562949953421312, 184549376, 0)
    ]


# Just return a single device so the psutil portion of the check doesn't fail
# The real data to check against is in mock_get_usage.
def get_mock_devices():

    device_tuple = collections.namedtuple('device_tuple', 'device mountpoint fstype opts')

    return [
        device_tuple(
            device='/dev/disk1',
            mountpoint='/',
            fstype='btrfs',
            opts='local,multilabel'
        )
    ]


@mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions', return_value=get_mock_devices())
@mock.patch('datadog_checks.btrfs.btrfs.BTRFS.get_usage', return_value=mock_get_usage())
def test_check(mock_get_usage, mock_device_list, aggregator):
    """
    Testing Btrfs check.
    """
    with mock.patch.object(btrfs_check, 'get_unallocated_space', return_value=None):
        btrfs_check.check({})

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
