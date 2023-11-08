# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.utils import ON_WINDOWS, get_metadata_metrics

if ON_WINDOWS:
    EXPECTED_DEVICES = ['c:']
    EXPECTED_METRICS = [
        'system.disk.free',
        'system.disk.in_use',
        'system.disk.total',
        'system.disk.used',
        'system.disk.utilized',
    ]
else:
    EXPECTED_DEVICES = ['overlay', 'shm', 'tmpfs', '/dev/sdb1']
    EXPECTED_METRICS = [
        'system.disk.free',
        'system.disk.in_use',
        'system.disk.total',
        'system.disk.used',
        'system.disk.utilized',
        'system.fs.inodes.free',
        'system.fs.inodes.in_use',
        'system.fs.inodes.total',
        'system.fs.inodes.used',
        'system.fs.inodes.utilized',
    ]


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()
    for metric in EXPECTED_METRICS:
        for device in EXPECTED_DEVICES:
            # `/dev/sdb1` device is flaky on the CI environment
            at_least = 0 if device == '/dev/sdb1' else 1
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, device=device, at_least=at_least)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
