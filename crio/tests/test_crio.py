# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import pytest
import mock

from datadog_checks.crio import CrioCheck

instance = {
    'prometheus_url': 'http://localhost:10249/metrics',
}

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
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"}
        )
    ):
        yield


def test_crio(aggregator, mock_data):
    """
    Testing crio.
    """

    c = CrioCheck(CHECK_NAME, None, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.operations.count')
    aggregator.assert_metric(NAMESPACE + '.operations.latency.count')
    aggregator.assert_metric(NAMESPACE + '.operations.latency.sum')
    aggregator.assert_metric(NAMESPACE + '.operations.latency.quantile')
    aggregator.assert_metric(NAMESPACE + '.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.mem.virtual')
    aggregator.assert_all_metrics_covered()
