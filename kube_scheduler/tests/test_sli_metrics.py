# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.kube_scheduler import KubeSchedulerCheck

from .common import make_mock_metrics

# Constants
CHECK_NAME = 'kube_scheduler'


@pytest.fixture()
def mock_metrics(mock_openmetrics_http):
    return make_mock_metrics(mock_openmetrics_http, 'metrics_slis_1.27.3.txt')


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


@pytest.mark.parametrize(
    'status_code, expected_available',
    [(200, True), (404, False), (403, False)],
    ids=['200_available', '404_unavailable', '403_unavailable'],
)
def test_detect_sli_endpoint(mock_openmetrics_http, instance, status_code, expected_available):
    mock_openmetrics_http.get.return_value = MockHTTPResponse(status_code=status_code)
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    assert c._slis_available is expected_available
