# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.istio import Istio

from .common import CITADEL_METRICS, GALLEY_METRICS, MESH_METRICS, NEW_MIXER_METRICS, PILOT_METRICS

INTERMITTENT_METRICS = ['istio.mesh.request.count', 'istio.pilot.mcp_sink.recv_failures_total']


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric in MESH_METRICS + NEW_MIXER_METRICS + GALLEY_METRICS + PILOT_METRICS + CITADEL_METRICS:
        if metric in INTERMITTENT_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('istio.pilot.prometheus.health', Istio.OK)
    aggregator.assert_service_check('istio.galley.prometheus.health', Istio.OK)
    aggregator.assert_service_check('istio.citadel.prometheus.health', Istio.OK)
