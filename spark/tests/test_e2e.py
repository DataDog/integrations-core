# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.spark import SparkCheck

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(common.INSTANCE_STANDALONE, rate=True)

    for metric in common.EXPECTED_E2E_METRICS:
        aggregator.assert_metric(metric)

    for metric in common.FLAKY_E2E_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        'spark.application_master.can_connect',
        status=SparkCheck.OK,
    )
    aggregator.assert_service_check(
        'spark.standalone_master.can_connect',
        status=SparkCheck.OK,
        tags=['url:http://spark-master:8080'] + common.CLUSTER_TAGS,
    )
