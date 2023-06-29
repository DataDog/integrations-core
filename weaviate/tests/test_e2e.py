# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import E2E_METRICS


@pytest.mark.e2e
def test_e2e_openmetrics_v1(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    aggregator.assert_service_check('weaviate.openmetrics.health', ServiceCheck.OK, count=2)

    for metric in E2E_METRICS:
        if metric == 'weaviate.node.shard.objects':
            aggregator.assert_metric(metric, at_least = 0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
