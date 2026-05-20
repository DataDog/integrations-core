# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.kube_dns import KubeDNSCheck

from .common import make_mock_metrics

customtag = "custom:tag"

instance = {'prometheus_endpoint': 'http://localhost:10055/metrics', 'tags': [customtag]}


@pytest.fixture()
def mock_get(mock_openmetrics_http):
    return make_mock_metrics(mock_openmetrics_http, 'metrics.txt')


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

    def test_check(self, aggregator, mock_get, mock_healthcheck_wrapper):
        """
        Testing kube_dns check.
        """

        check = KubeDNSCheck('kube_dns', {}, [instance])
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

    @pytest.mark.parametrize(
        'side_effect, expected_status, expected_message',
        [
            (None, AgentCheck.OK, None),
            (requests.HTTPError('health check failed'), AgentCheck.CRITICAL, 'health check failed'),
        ],
        ids=['ok', 'http_error'],
    )
    def test_service_check(self, monkeypatch, side_effect, expected_status, expected_message):
        instance_tags = [customtag]
        check = KubeDNSCheck(self.CHECK_NAME, {}, [instance])
        monkeypatch.setattr(check, 'service_check', mock.Mock())

        healthcheck_url = check.instance['health_url']
        handler = mock.MagicMock()
        handler.get.return_value.raise_for_status = mock.Mock(side_effect=side_effect)
        check._http_handlers[healthcheck_url] = handler

        check._perform_service_check(instance)

        expected_kwargs = {'tags': instance_tags}
        if expected_message is not None:
            expected_kwargs['message'] = expected_message
        check.service_check.assert_called_with(self.NAMESPACE + '.up', expected_status, **expected_kwargs)
