# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest
import requests_mock

from datadog_checks.kube_controller_manager import KubeControllerManagerCheck

from .common import HERE

# Constants
CHECK_NAME = 'kube_controller_manager'


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(HERE, 'fixtures', 'metrics_slis_1.27.3.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


def test_check_metrics_slis(aggregator, mock_metrics, mock_request, instance):
    mock_request.get('http://localhost:10257/metrics/slis', status_code=200)
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:attachdetach', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:bootstrapsigner', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:clusterrole-aggregation', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck', value=1, metric_type=aggregator.GAUGE, tags=['sli_name:cronjob', 'type:healthz']
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:csrapproving', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:csrcleaner', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:csrsigning', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:daemonset', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:deployment', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthcheck',
        value=1,
        metric_type=aggregator.GAUGE,
        tags=['sli_name:disruption', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:attachdetach', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:bootstrapsigner', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:clusterrole-aggregation', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:cronjob', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:csrapproving', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:csrcleaner', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:csrsigning', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:daemonset', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:deployment', 'status:success', 'type:healthz'],
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        value=423,
        tags=['sli_name:disruption', 'status:success', 'type:healthz'],
    )
    aggregator.assert_all_metrics_covered()


def test_check_metrics_slis_transform(aggregator, mock_metrics, mock_request, instance):
    mock_request.get('http://localhost:10257/metrics/slis', status_code=200)
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    # Check that no metrics with `name` tag come through
    assert_metric(
        'slis.kubernetes_healthcheck', count=0, metric_type=aggregator.GAUGE, tags=['name:attachdetach', 'type:healthz']
    )
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        metric_type=aggregator.MONOTONIC_COUNT,
        count=0,
        tags=['name:attachdetach', 'status:success', 'type:healthz'],
    )


def test_check_metrics_slis_filter_by_type(aggregator, mock_metrics, mock_request, instance):
    mock_request.get('http://localhost:10257/metrics/slis', status_code=200)
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


@pytest.fixture()
def mock_request():
    with requests_mock.Mocker() as m:
        yield m


def test_detect_sli_endpoint(mock_metrics, instance):
    with mock.patch('requests.get') as mock_request:
        mock_request.return_value.status_code = 200
        c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
        c.check(instance)
        assert c._slis_available is True


def test_detect_sli_endpoint_404(mock_metrics, instance):
    with mock.patch('requests.get') as mock_request:
        mock_request.return_value.status_code = 404
        c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
        c.check(instance)
        assert c._slis_available is False


def test_detect_sli_endpoint_403(mock_metrics, mock_request, instance):
    with mock.patch('requests.get') as mock_request:
        mock_request.return_value.status_code = 403
        c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
        c.check(instance)
        assert c._slis_available is False
