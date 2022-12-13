# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.kube_metrics_server import KubeMetricsServerCheck

instance = {
    'prometheus_url': 'https://localhost:443/metrics',
    'send_histograms_buckets': True,
    'health_service_check': True,
}

# Constants
CHECK_NAME = 'kube_metrics_server'
NAMESPACE = 'kube_metrics_server'


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


def test_check_metrics(aggregator, mock_metrics):
    c = KubeMetricsServerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.authenticated_user.requests', value=141.0, tags=['username:other'])
    assert_metric('.kubelet_summary_scrapes_total', value=17.0, tags=['success:false'])
    assert_metric('.manager_tick_duration.sum', value=40.568365077999985, tags=[])
    assert_metric('.manager_tick_duration.count', value=17.0, tags=[])
    assert_metric('.scraper_duration.sum', value=0.000137543, tags=['source:kubelet_summary:ci-host'])
    assert_metric('.scraper_duration.count', value=17.0, tags=['source:kubelet_summary:ci-host', 'upper_bound:none'])
    assert_metric('.kubelet_summary_request_duration.sum', value=1.5491e-05, tags=['node:ci-host'])
    assert_metric('.kubelet_summary_request_duration.count', value=17, tags=['node:ci-host', 'upper_bound:none'])
    assert_metric('.scraper_last_time', value=1.555673692e09, tags=['source:kubelet_summary:ci-host'])
    assert_metric('.process.max_fds', value=1.048576e06, tags=[])
    assert_metric('.process.open_fds', value=10.0, tags=[])
    assert_metric('.go.gc_duration_seconds.sum', value=0.007900459, tags=[])
    assert_metric('.go.gc_duration_seconds.count', value=19.0, tags=[])
    assert_metric('.go.gc_duration_seconds.quantile')
    assert_metric('.go.goroutines', value=51.0, tags=[])
    aggregator.assert_service_check(NAMESPACE + ".prometheus.health")
    aggregator.assert_all_metrics_covered()


def test_service_check_ok(monkeypatch):
    instance_tags = []

    check = KubeMetricsServerCheck(CHECK_NAME, {}, [instance])

    monkeypatch.setattr(check, 'service_check', mock.Mock())

    calls = [
        mock.call(NAMESPACE + '.up', AgentCheck.OK, tags=instance_tags),
        mock.call(NAMESPACE + '.up', AgentCheck.CRITICAL, tags=instance_tags, message='health check failed'),
    ]

    # successful health check
    with mock.patch("requests.get", return_value=mock.MagicMock(status_code=200)):
        check._perform_service_check(instance)

    # failed health check
    raise_error = mock.Mock()
    raise_error.side_effect = requests.HTTPError('health check failed')
    with mock.patch("requests.get", return_value=mock.MagicMock(raise_for_status=raise_error)):
        check._perform_service_check(instance)

    check.service_check.assert_has_calls(calls)
