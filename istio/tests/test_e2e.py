# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.istio import Istio

from .common import CITADEL_METRICS, GALLEY_METRICS, MESH_METRICS, NEW_MIXER_METRICS, PILOT_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric in MESH_METRICS + NEW_MIXER_METRICS + GALLEY_METRICS + PILOT_METRICS + CITADEL_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('istio.pilot.prometheus.health', Istio.OK)
    aggregator.assert_service_check('istio.galley.prometheus.health', Istio.OK)
    aggregator.assert_service_check('istio.citadel.prometheus.health', Istio.OK)
