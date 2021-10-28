# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.istio import Istio

from .common import ISTIOD_METRICS

INTERMITTENT_METRICS = [
    'istio.mesh.request.count',
    'istio.pilot.mcp_sink.recv_failures_total',
    'istio.galley.validation.passed',
    'istio.pilot.rds_expired_nonce',
]


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    metrics = ISTIOD_METRICS
    aggregator.assert_service_check('istio.prometheus.health', Istio.OK)

    for metric in metrics:
        if metric in INTERMITTENT_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)
