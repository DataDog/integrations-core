# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from mock import Mock
from prometheus_client import Metric

from datadog_checks.base.checks.openmetrics.v2.labels import LabelAggregator


def _metric(name, labels):
    metric = Metric(name, 'help', 'gauge')
    metric.add_sample(name, labels, 1)
    return metric


def _metrics_with_tripwire(n_after_source):
    """Yields the source metric first, then `n_after_source` more. Raises if pulled past that point,
    so consuming more than necessary (i.e. buffering the whole payload) fails the test loudly."""
    yield _metric('app_info', {'region': 'us'})
    for i in range(n_after_source):
        yield _metric('unrelated', {'i': str(i)})
    raise AssertionError('consumed past the last metric needed for shared labels')


def test_share_labels_only_stops_consuming_once_source_found():
    """Regression test: `target_info_metric` must not stay truthy forever when `target_info` isn't
    configured, otherwise the early-exit never fires and the whole payload gets buffered regardless
    of `share_labels` alone finding its source metric early.
    """
    aggregator = LabelAggregator(Mock(), {'share_labels': {'app_info': True}})

    cached = aggregator.collect_until_configs_found(_metrics_with_tripwire(n_after_source=1000))

    assert len(cached) == 1
    assert cached[0].name == 'app_info'
