# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import platform

import pytest

from datadog_checks.istio import Istio

from .common import ISTIOD_METRICS, ISTIOD_V2_METRICS

INTERMITTENT_METRICS = [
    'istio.citadel.server.cert_chain_expiry_timestamp',
    'istio.mesh.request.count',
    'istio.pilot.mcp_sink.recv_failures_total',
    'istio.galley.validation.passed',
    'istio.pilot.rds_expired_nonce',
    'istio.galley.validation.config_update_error.count',
    'istio.galley.validation.config_update_error',
    'istio.pilot.conflict.outbound_listener.http_over_https',
    'istio.pilot.xds.eds_all_locality_endpoints',
    'istio.pilot.xds.eds_instances',
    "istio.pilot.k8s.cfg_events",
    "istio.pilot.k8s.cfg_events.count",
    "istio.sidecar_injection.requests_total",
    "istio.sidecar_injection.requests.count",
    "istio.sidecar_injection.success_total",
    "istio.sidecar_injection.success.count",
    "istio.sidecar_injection.failure_total",
    "istio.sidecar_injection.failure.count",
    "istio.sidecar_injection.skip_total",
    "istio.sidecar_injection.skip.count",
]


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
def test_e2e_openmetrics_v2(dd_agent_check, instance_openmetrics_v2):
    aggregator = dd_agent_check(instance_openmetrics_v2, rate=True)

    metrics = ISTIOD_V2_METRICS
    aggregator.assert_service_check('istio.openmetrics.health', Istio.OK)

    for metric in metrics:
        if metric in INTERMITTENT_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)
