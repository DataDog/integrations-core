# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPConnectionError, HTTPStatusError
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
        'side_effect, expected_status, extra_kwargs',
        [
            (None, AgentCheck.OK, {}),
            (HTTPStatusError('health check failed'), AgentCheck.CRITICAL, {'message': 'health check failed'}),
            (HTTPConnectionError('connection refused'), AgentCheck.CRITICAL, {'message': 'connection refused'}),
        ],
        ids=['ok', 'http_error', 'http_connection_error'],
    )
    def test_service_check(self, monkeypatch, side_effect, expected_status, extra_kwargs):
        instance_tags = [customtag]
        check = KubeDNSCheck(self.CHECK_NAME, {}, [instance])
        monkeypatch.setattr(check, 'service_check', mock.Mock())

        healthcheck_url = check.instance['health_url']
        handler = mock.MagicMock()
        handler.get.return_value.raise_for_status = mock.Mock(side_effect=side_effect)
        check._http_handlers[healthcheck_url] = handler

        check._perform_service_check(instance)

        check.service_check.assert_called_with(
            self.NAMESPACE + '.up', expected_status, tags=instance_tags, **extra_kwargs
        )

    @pytest.mark.parametrize(
        ('instance_overrides', 'expected_verify', 'expected_ignore_warning'),
        [
            pytest.param({}, False, True, id='no ca cert'),
            pytest.param({'ssl_ca_cert': '/etc/ca.crt'}, '/etc/ca.crt', False, id='ca cert configured'),
        ],
    )
    def test_healthcheck_client_carries_instance_tls_config(
        self, instance_overrides, expected_verify, expected_ignore_warning
    ):
        """The healthcheck builds its own client, so the instance TLS settings have to reach it.

        With no CA certificate configured it falls back to an unverified connection with the warning
        suppressed, which is what an endpoint serving a self-signed certificate depends on.
        """
        check = KubeDNSCheck(self.CHECK_NAME, {}, [{**instance, **instance_overrides}])
        health_url = check.instance['health_url']

        handler = check._healthcheck_http_handler(check.instance, health_url)

        assert handler.options['verify'] == expected_verify
        assert handler.ignore_tls_warning is expected_ignore_warning
        # Cached per endpoint, so repeated healthchecks reuse one client rather than building each time.
        assert check._healthcheck_http_handler(check.instance, health_url) is handler
