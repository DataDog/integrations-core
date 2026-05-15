# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.kube_scheduler import KubeSchedulerCheck

from .common import HERE

# Constants
CHECK_NAME = 'kube_scheduler'


@pytest.fixture()
def mock_metrics(mock_openmetrics_http):
    f_name = os.path.join(HERE, 'fixtures', 'metrics_slis_1.27.3.txt')
    mock_openmetrics_http.get.return_value = MockHTTPResponse(file_path=f_name, headers={'Content-Type': 'text/plain'})
    yield mock_openmetrics_http


def test_check_metrics_slis(aggregator, mock_metrics, instance):
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    assert_metric('slis.kubernetes_healthcheck', value=1, tags=['sli_name:ping'])
    assert_metric(
        'slis.kubernetes_healthchecks_total',
        value=2450,
        tags=['sli_name:ping', 'status:success'],
    )

    aggregator.assert_all_metrics_covered()


def test_check_metrics_slis_transform(aggregator, mock_metrics, instance):
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
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
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
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


def test_detect_sli_endpoint(mock_openmetrics_http, instance):
    mock_openmetrics_http.get.return_value = MockHTTPResponse(status_code=200)
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    assert c._slis_available is True


def test_detect_sli_endpoint_404(mock_openmetrics_http, instance):
    mock_openmetrics_http.get.return_value = MockHTTPResponse(status_code=404)
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    assert c._slis_available is False


def test_detect_sli_endpoint_403(mock_openmetrics_http, instance):
    mock_openmetrics_http.get.return_value = MockHTTPResponse(status_code=403)
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    assert c._slis_available is False
