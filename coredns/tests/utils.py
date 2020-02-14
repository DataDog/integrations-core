# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .common import COUNT_METRICS


def _assert_metric(aggregator, metric):
    if metric in COUNT_METRICS:
        aggregator.assert_metric(metric, metric_type=aggregator.MONOTONIC_COUNT)
    else:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)
