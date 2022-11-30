# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception):
        dd_agent_check(instance, rate=True)
    endpoint_tag = "endpoint:" + instance.get('prometheus_url')
    tags = instance.get('tags', []) + [endpoint_tag]
    aggregator.assert_service_check("kube_apiserver.prometheus.health", AgentCheck.CRITICAL, count=2, tags=tags)
