# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import os

import mock
import pytest

# project
from datadog_checks.kube_dns import KubeDNSCheck

customtag = "custom:tag"

instance = {'prometheus_endpoint': 'http://localhost:10055/metrics', 'tags': [customtag]}


@pytest.fixture()
def mock_get():
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


@pytest.fixture
def aggregator():
    from datadog_checks.base.stubs import aggregator

    aggregator.reset()
    return aggregator


class TestKubeDNS:
    """Basic Test for kube_dns integration."""

    CHECK_NAME = 'kube_dns'
    NAMESPACE = 'kubedns'
    METRICS = [
        NAMESPACE + '.response_size.bytes.count',
        NAMESPACE + '.response_size.bytes.sum',
        NAMESPACE + '.request_duration.seconds.count',
        NAMESPACE + '.request_duration.seconds.sum',
        NAMESPACE + '.request_count',
        NAMESPACE + '.error_count',
        NAMESPACE + '.cachemiss_count',
    ]
    COUNT_METRICS = [
        NAMESPACE + '.request_count.count',
        NAMESPACE + '.error_count.count',
        NAMESPACE + '.cachemiss_count.count',
    ]

    def test_check(self, aggregator, mock_get):
        """
        Testing kube_dns check.
        """

        check = KubeDNSCheck('kube_dns', {}, {}, [instance])
        check.check(instance)

        # check that we then get the count metrics also
        check.check(instance)
        for metric in self.METRICS + self.COUNT_METRICS:
            aggregator.assert_metric(metric)
            aggregator.assert_metric_has_tag(metric, customtag)

        aggregator.assert_all_metrics_covered()

        # Make sure instance tags are not modified, see #3066
        aggregator.reset()
        check.check(instance)
        name = self.NAMESPACE + ".request_duration.seconds.sum"
        aggregator.assert_metric(name)
        aggregator.assert_metric(name, tags=['custom:tag', 'system:reverse'])
