# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from datadog_checks.btrfs import BTRFS

import mock
import pytest

btrfs_check = BTRFS('btrfs', {}, {})


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def mock_get_usage(mountpoint):
    return [
        (1, 9672065024, 9093722112),
        (34, 33554432, 16384),
        (36, 805306368, 544276480),
        (562949953421312, 184549376, 0)
    ]


def test_check(aggregator):
    """
    Testing Btrfs check.
    """
    with mock.patch.object(
        btrfs_check,
        'get_usage',
        side_effect=mock_get_usage
    ):
        btrfs_check.check({})

    aggregator.assert_metric('system.disk.btrfs.total', at_least=0)
    aggregator.assert_metric('system.disk.btrfs.used', at_least=0)
    aggregator.assert_metric('system.disk.btrfs.free', at_least=0)
    aggregator.assert_metric('system.disk.btrfs.usage', at_least=0)

    assert aggregator.metrics_asserted_pct == 100
