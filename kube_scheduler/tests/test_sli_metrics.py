# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

from datadog_checks.kube_scheduler import KubeSchedulerCheck

instance = {'prometheus_url': 'http://localhost:10251/metrics/slis', 'send_histograms_buckets': True}

# Constants
CHECK_NAME = 'kube_scheduler'
NAMESPACE = 'kube_scheduler'


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics_slis_1.27.3.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


def test_check_metrics_slis(aggregator, mock_metrics):
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.slis.kubernetes_healthcheck', value=1, tags=['name:ping', 'type:healthz'])
    assert_metric(
        '.slis.kubernetes_healthchecks_total', value=2450, tags=['name:ping', 'status:success', 'type:healthz']
    )

    aggregator.assert_all_metrics_covered()
