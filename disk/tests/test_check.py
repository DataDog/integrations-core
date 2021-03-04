# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from itertools import chain

from datadog_checks.disk import Disk


def test_check(aggregator, instance_basic_volume, gauge_metrics, rate_metrics, count_metrics):
    """
    Basic check to see if all metrics are there
    """
    c = Disk('disk', {}, [instance_basic_volume])
    c.check(instance_basic_volume)

    for name in chain(gauge_metrics, rate_metrics, count_metrics):
        aggregator.assert_metric(name)

    aggregator.assert_all_metrics_covered()
