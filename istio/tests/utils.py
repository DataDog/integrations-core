# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.istio.constants import BLACKLIST_LABELS

from .common import COUNT_METRICS


def _assert_tags_excluded(aggregator, addl_blacklist):
    """
    Test excluded labels
    """
    fail = 0
    for _, stubs in aggregator._metrics.items():
        for stub in stubs:
            for tag in stub.tags:
                for excluded_tag in BLACKLIST_LABELS + addl_blacklist:
                    if tag.startswith(excluded_tag + ':'):
                        fail += 1
    assert fail == 0
    aggregator.assert_all_metrics_covered()


def _assert_metric(aggregator, metric):
    if metric in COUNT_METRICS:
        aggregator.assert_metric(metric, metric_type=aggregator.MONOTONIC_COUNT)
    else:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)
