# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .common import assert_metrics


def test_metrics(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    assert_metrics(aggregator)


def test_metrics_classic_histograms(dd_agent_check, instance):
    # Without histogram_buckets_as_distributions, histograms submit classic bucket/count/sum metrics,
    # which exercises metadata.csv rows that `test_metrics` above never touches.
    classic_instance = {key: value for key, value in instance.items() if key != 'histogram_buckets_as_distributions'}
    aggregator = dd_agent_check(classic_instance, rate=True)
    assert_metrics(aggregator)
