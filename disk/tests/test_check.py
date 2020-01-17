# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys
from itertools import chain

import pytest

from datadog_checks.disk import Disk

from . import common


def test_check(aggregator, instance_basic_volume, gauge_metrics, rate_metrics):
    """
    Basic check to see if all metrics are there
    """
    c = Disk('disk', {}, [instance_basic_volume])
    c.check(instance_basic_volume)

    for name in chain(gauge_metrics, rate_metrics):
        aggregator.assert_metric(name)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform != 'linux', reason='disk labels are only available on Linux')
@pytest.mark.usefixtures('psutil_mocks')
def test_instance_with_blkid_cache_file(aggregator, instance_blkid_cache_file):
    """
    Verify that the disk labels are set with when the blkid_cache_file option is set
    """
    c = Disk('disk', {}, [instance_blkid_cache_file])
    c.check(instance_blkid_cache_file)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(
            metric['metric'], metric_type=aggregator.GAUGE, tags=['device:/dev/sda1', 'label:MYLABEL']
        )
