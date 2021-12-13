# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.crio import CrioCheck

CHECK_NAME = 'crio'
NAMESPACE = 'crio'


@pytest.fixture()
def mock_data():
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


def test_crio(aggregator, mock_data, instance):
    """
    Testing crio.
    """

    c = CrioCheck(CHECK_NAME, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.operations.count')
    aggregator.assert_metric(NAMESPACE + '.operations.latency.count')
    aggregator.assert_metric(NAMESPACE + '.operations.latency.sum')
    aggregator.assert_metric(NAMESPACE + '.operations.latency.quantile')
    aggregator.assert_metric(NAMESPACE + '.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.mem.virtual')
    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception):
        dd_agent_check(instance, rate=True)
    tag = "endpoint:" + instance.get('prometheus_url')
    aggregator.assert_service_check("crio.prometheus.health", AgentCheck.CRITICAL, count=2, tags=[tag])
