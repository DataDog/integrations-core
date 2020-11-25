# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.spark import SparkCheck

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(common.INSTANCE_STANDALONE, rate=True)

    for metric in common.EXPECTED_E2E_METRICS:
        aggregator.assert_metric(metric)

    for metric in ['avg_input_rate', 'avg_scheduling_delay']:
        # Flaky metrics
        aggregator.assert_metric("spark.streaming.statistics.{}".format(metric), at_least=0)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'spark.application_master.can_connect',
        status=SparkCheck.OK,
    )
    aggregator.assert_service_check(
        'spark.standalone_master.can_connect',
        status=SparkCheck.OK,
        tags=['cluster_name:SparkCluster', 'url:http://spark-master:8080'],
    )
