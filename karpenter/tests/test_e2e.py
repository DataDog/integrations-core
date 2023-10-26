# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# from datadog_checks.dev.utils import get_metadata_metrics

from . import common


def test_check_karpenter_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    metrics = common.TEST_METRICS

    for metric in metrics:
        aggregator.assert_metric(name=metric)

    aggregator.assert_all_metrics_covered()
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())
