# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.spark import SparkCheck

from . import common


@pytest.mark.e2e
@pytest.mark.skipif(os.environ.get('SPARK_PLATFORM') == 'k8s', reason='Docker standalone test')
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
@pytest.mark.skipif(os.environ.get('SPARK_PLATFORM') != 'k8s', reason='K8s driver-mode test')
def test_e2e_driver_k8s(dd_agent_check):
    aggregator = dd_agent_check(common.INSTANCE_DRIVER_K8S, rate=True)

    for metric in common.EXPECTED_E2E_DRIVER_K8S_METRICS:
        aggregator.assert_metric(metric)

    for metric in common.FLAKY_E2E_DRIVER_K8S_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        'spark.driver.can_connect',
        status=SparkCheck.OK,
        tags=['url:{}'.format(common.INSTANCE_DRIVER_K8S['spark_url'])] + common.K8S_CLUSTER_TAGS,
    )


@pytest.mark.e2e
@pytest.mark.skipif(os.environ.get('SPARK_PLATFORM') != 'k8s', reason='K8s driver-mode discovery test')
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(check_rate=True)

    for metric in common.EXPECTED_E2E_DRIVER_K8S_METRICS:
        aggregator.assert_metric(metric)

    for metric in common.FLAKY_E2E_DRIVER_K8S_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        'spark.driver.can_connect',
        status=SparkCheck.OK,
    )


@pytest.mark.e2e
@pytest.mark.skipif(os.environ.get('SPARK_PLATFORM') != 'k8s', reason='K8s discovery candidate stability test')
def test_e2e_discovery_all_candidates(dd_agent_check, spark_kubeconfig):
    assert_all_discovery_candidates_stable_kubernetes(
        dd_agent_check,
        SparkCheck,
        spark_kubeconfig,
        namespace=common.K8S_SPARK_NAMESPACE,
        pod_selector='app=spark-driver',
    )
