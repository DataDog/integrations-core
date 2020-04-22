# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.istio import Istio

from .common import (
    CITADEL_METRICS,
    GALLEY_METRICS,
    ISTIOD_METRICS,
    MESH_METRICS,
    MESH_METRICS_1_4,
    NEW_MIXER_METRICS,
    PILOT_METRICS,
)

INTERMITTENT_METRICS = [
    'istio.mesh.request.count',
    'istio.pilot.mcp_sink.recv_failures_total',
    'istio.galley.validation.passed',
    'istio.pilot.rds_expired_nonce',
]

LEGACY_METRICS = MESH_METRICS + MESH_METRICS_1_4 + NEW_MIXER_METRICS + GALLEY_METRICS + PILOT_METRICS + CITADEL_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    version = os.environ.get('ISTIO_VERSION')
    aggregator = dd_agent_check(rate=True)

    metrics = LEGACY_METRICS
    if version == '1.5.1':
        metrics = ISTIOD_METRICS
        aggregator.assert_service_check('istio.prometheus.health', Istio.OK)
    else:
        aggregator.assert_service_check('istio.pilot.prometheus.health', Istio.OK)
        aggregator.assert_service_check('istio.galley.prometheus.health', Istio.OK)
        aggregator.assert_service_check('istio.citadel.prometheus.health', Istio.OK)

    for metric in metrics:
        if metric in INTERMITTENT_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
