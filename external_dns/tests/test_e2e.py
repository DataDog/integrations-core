# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from .common import OPENMETRICS_HEALTH_TAGS, PROMETHEUS_HEALTH_TAGS


@pytest.mark.e2e
@pytest.mark.parametrize(
    'instance_fixture,service_check,tags',
    [
        ('instance', 'external_dns.prometheus.health', PROMETHEUS_HEALTH_TAGS),
        ('instance_e2e_omv2', 'external_dns.openmetrics.health', OPENMETRICS_HEALTH_TAGS),
    ],
    ids=['omv1', 'omv2'],
)
def test_e2e(dd_agent_check, aggregator, request, instance_fixture, service_check, tags):
    """Both integration versions raise and report CRITICAL on their respective health check."""
    instance = request.getfixturevalue(instance_fixture)
    with pytest.raises(Exception):
        dd_agent_check(instance, rate=True)
    aggregator.assert_service_check(service_check, AgentCheck.CRITICAL, count=2, tags=tags)
