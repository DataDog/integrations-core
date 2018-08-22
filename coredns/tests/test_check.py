# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.coredns import CoreDNSCheck

import mock
import os
import pytest

instance = {
    'prometheus_endpoint': 'http://localhost:9153/metrics',
}

# Constants
CHECK_NAME = 'coredns'
NAMESPACE = 'coredns'


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture()
def mock_coredns():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_coredns = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"}
        )
    )
    yield mock_coredns.start()
    mock_coredns.stop()


def test_check(aggregator, mock_coredns):
    c = CoreDNSCheck(CHECK_NAME, None, {}, instance)
    c.check(instance)

    aggregator.assert_metric(NAMESPACE + '.response_code_count')
    aggregator.assert_metric(NAMESPACE + '.response_code_count.count')
    aggregator.assert_metric(NAMESPACE + '.proxy_request_count')
    aggregator.assert_metric(NAMESPACE + '.proxy_request_count.count')
    aggregator.assert_metric(NAMESPACE + '.cache_hits_count')
    aggregator.assert_metric(NAMESPACE + '.cache_hits_count.count')
    aggregator.assert_metric(NAMESPACE + '.cache_misses_count')
    aggregator.assert_metric(NAMESPACE + '.cache_misses_count.count')
    aggregator.assert_metric(NAMESPACE + '.request_count')
    aggregator.assert_metric(NAMESPACE + '.request_count.count')
    aggregator.assert_metric(NAMESPACE + '.request_type_count')
    aggregator.assert_metric(NAMESPACE + '.request_type_count.count')
    aggregator.assert_metric(NAMESPACE + '.request_duration.seconds.sum')
    aggregator.assert_metric(NAMESPACE + '.request_duration.seconds.count')
    aggregator.assert_metric(NAMESPACE + '.proxy_request_duration.seconds.sum')
    aggregator.assert_metric(NAMESPACE + '.proxy_request_duration.seconds.count')
    aggregator.assert_metric(NAMESPACE + '.request_size.bytes.sum')
    aggregator.assert_metric(NAMESPACE + '.request_size.bytes.count')
    aggregator.assert_metric(NAMESPACE + '.cache_size.count')

    assert aggregator.metrics_asserted_pct == 100.0
