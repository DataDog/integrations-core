# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

from datadog_checks.external_dns import ExternalDNSCheck

customtag = "custom:tag"
instance = {'prometheus_url': 'http://localhost:7979/metrics', 'tags': [customtag]}

# Constants
NAME = 'external_dns'

DEFAULT_METRICS = [
    '.registry.endpoints.total',
    '.source.endpoints.total',
    '.source.errors.total',
    '.registry.errors.total',
]


@pytest.fixture()
def mock_external_dns():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_external_dns = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    )
    yield mock_external_dns.start()
    mock_external_dns.stop()


def test_external_dns(aggregator, mock_external_dns):
    """
    Testing external_dns
    """

    c = ExternalDNSCheck(NAME, None, {}, [instance])
    c.check(instance)
    for metric in DEFAULT_METRICS:
        aggregator.assert_metric(NAME + metric)
        aggregator.assert_metric_has_tag(NAME + metric, customtag)
    aggregator.assert_all_metrics_covered()
