# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import platform

import pytest

from datadog_checks.istio import Istio

from .common import ISTIOD_METRICS, ISTIOD_V2_METRICS

INTERMITTENT_METRICS = [
    'istio.mesh.request.count',
    'istio.pilot.mcp_sink.recv_failures_total',
    'istio.galley.validation.passed',
    'istio.pilot.rds_expired_nonce',
]


@pytest.mark.e2e
def test_e2e_openmetrics_v1(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    metrics = ISTIOD_METRICS
    aggregator.assert_service_check('istio.prometheus.health', Istio.OK)

    for metric in metrics:
        if metric in INTERMITTENT_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.e2e
def test_e2e_openmetrics_v2(dd_agent_check, instance_openmetrics_v2):
    aggregator = dd_agent_check(instance_openmetrics_v2, rate=True)

    metrics = ISTIOD_V2_METRICS
    aggregator.assert_service_check('istio.openmetrics.health', Istio.OK)

    for metric in metrics:
        if metric in INTERMITTENT_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)
