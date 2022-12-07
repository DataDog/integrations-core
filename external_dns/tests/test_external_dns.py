# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.external_dns import ExternalDNSCheck
from datadog_checks.external_dns.metrics import DEFAULT_METRICS

from .common import CHECK_NAME


@pytest.mark.usefixtures('mock_external_dns')
def test_external_dns(aggregator, dd_run_check, instance):
    """
    Testing external_dns
    """

    c = ExternalDNSCheck('external_dns', {}, [instance])
    dd_run_check(c)

    for metric in DEFAULT_METRICS.values():
        metric = '{}.{}'.format(CHECK_NAME, metric)
        for tag in instance['tags']:
            aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_all_metrics_covered()


# Minimal E2E testing
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception):
        dd_agent_check(instance, rate=True)
    endpoint_tag = "endpoint:" + instance.get('prometheus_url')
    tags = instance.get('tags').append(endpoint_tag)
    aggregator.assert_service_check("external_dns.prometheus.health", AgentCheck.CRITICAL, count=2, tags=tags)
