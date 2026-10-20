# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.kube_controller_manager import KubeControllerManagerCheck

from .common import register_metrics

# Constants
CHECK_NAME = 'kube_controller_manager'


@pytest.fixture()
def mock_metrics(fake_http, fake_http_response, instance):
    register_metrics(fake_http_response, 'metrics_slis_1.27.3.txt', instance['prometheus_url'])
    yield
    fake_http.assert_all_responses_consumed()


def test_check_metrics_slis(aggregator, mock_metrics, instance):
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:attachdetach'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:bootstrapsigner'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:clusterrole-aggregation'],
    )
    assert_metric('slis.kubernetes_healthcheck', value=1, metric_type=aggregator.GAUGE, tags=['sli_name:cronjob'])
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:csrapproving'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:csrcleaner'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:csrsigning'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:daemonset'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:deployment'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:disruption'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:attachdetach', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:bootstrapsigner', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:clusterrole-aggregation', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:cronjob', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:csrapproving', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:csrcleaner', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:csrsigning', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:daemonset', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:deployment', 'status:success'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:disruption', 'status:success'],
    )
    aggregator.assert_all_metrics_covered()


def test_check_metrics_slis_transform(aggregator, mock_metrics, instance):
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    # Check that no metrics with `name` tag come through
    assert_metric('slis.kubernetes_healthcheck', count=0, metric_type=aggregator.GAUGE, tags=['name:attachdetach'])
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        count=0,
        tags=['name:attachdetach', 'status:success'],
    )


def test_check_metrics_slis_filter_by_type(aggregator, mock_metrics, instance):
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    # Check that metrics with type other than `healthz` are filtered out
    assert_metric(
        'slis.kubernetes_healthcheck', count=0, metric_type=aggregator.GAUGE, tags=['sli_name:etcd', 'type:readyz']
    )

    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        count=0,
        tags=['sli_name:etcd', 'status:success', 'type:readyz'],
    )


@pytest.mark.parametrize(
    'status_code, expected_available',
    [(200, True), (404, False), (403, False)],
    ids=['200_available', '404_unavailable', '403_unavailable'],
)
def test_detect_sli_endpoint(fake_http, instance, status_code, expected_available):
    fake_http.register_response('GET', instance['prometheus_url'] + '/slis', FakeHTTPResponse(status_code=status_code))
    KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    assert instance["slis_available"] is expected_available
