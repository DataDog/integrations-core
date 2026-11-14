# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
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


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)

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
    # discovery can't know the discovered container's real cluster_name/tags ahead of time
    # (they're synthesized placeholders), so the standalone_master service check's tags aren't
    # asserted here the way they are in test_e2e above.
    aggregator.assert_service_check(
        'spark.standalone_master.can_connect',
        status=SparkCheck.OK,
    )


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, SparkCheck, compose_service='spark-master')
