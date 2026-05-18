# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import platform

import pytest
from packaging.version import InvalidVersion, Version

from datadog_checks.istio import Istio

from .common import ISTIOD_METRICS, ISTIOD_V2_METRICS, V2_WAYPOINT_METRICS, V2_ZTUNNEL_METRICS

ISTIO_MODE = os.environ.get("ISTIO_MODE", "sidecar")
ISTIO_VERSION = os.environ.get("ISTIO_VERSION", "")

# Metrics that are only emitted when a specific condition occurs (validation failures,
# listener conflicts, sidecar injection events, traffic, etc.). These should never be
# strictly asserted because the e2e cluster does not always reproduce the condition.
INTERMITTENT_METRICS = [
    'istio.citadel.server.cert_chain_expiry_timestamp',
    'istio.mesh.request.count',
    'istio.pilot.mcp_sink.recv_failures_total',
    'istio.galley.validation.passed',
    'istio.galley.validation.passed.count',
    'istio.galley.validation.failed',
    'istio.galley.validation.failed.count',
    'istio.pilot.rds_expired_nonce',
    'istio.galley.validation.config_update_error.count',
    'istio.galley.validation.config_update_error',
    'istio.pilot.conflict.inbound_listener',
    'istio.pilot.conflict.outbound_listener.http_over_current_tcp',
    'istio.pilot.conflict.outbound_listener.http_over_https',
    'istio.pilot.conflict.outbound_listener.tcp_over_current_http',
    'istio.pilot.conflict.outbound_listener.tcp_over_current_tcp',
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

# Metrics that Istio 1.13's binary still emits but newer Go runtimes (and the matching
# client_golang version shipped with Istio 1.24+) no longer expose. They are strictly
# asserted on 1.13 to keep that environment's safety net intact, and skipped on later
# versions where the binary no longer produces them at all.
LEGACY_GO_METRICS = {
    'istio.go.memstats.gc_cpu_fraction',
    'istio.go.memstats.lookups_total',
    'istio.go.memstats.lookups.count',
}

AMBIENT_GA_VERSION = Version("1.24")


def _is_legacy_istio(version: str) -> bool:
    try:
        return Version(version) < AMBIENT_GA_VERSION
    except InvalidVersion:
        return False


IS_LEGACY_ISTIO = _is_legacy_istio(ISTIO_VERSION)


def _assert_istiod_metric(aggregator, metric):
    if metric in LEGACY_GO_METRICS and not IS_LEGACY_ISTIO:
        return
    if metric in INTERMITTENT_METRICS:
        aggregator.assert_metric(metric, at_least=0)
    else:
        aggregator.assert_metric(metric)


@pytest.mark.skipif(ISTIO_MODE != "sidecar", reason="Sidecar-mode e2e: skipped on ambient envs")
def test_e2e_openmetrics_v1(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    aggregator.assert_service_check('istio.prometheus.health', Istio.OK)

    for metric in ISTIOD_METRICS:
        _assert_istiod_metric(aggregator, metric)


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.skipif(ISTIO_MODE != "sidecar", reason="Sidecar-mode e2e: skipped on ambient envs")
def test_e2e_openmetrics_v2(dd_agent_check, instance_openmetrics_v2):
    aggregator = dd_agent_check(instance_openmetrics_v2, rate=True)

    aggregator.assert_service_check('istio.openmetrics.health', Istio.OK)

    for metric in ISTIOD_V2_METRICS:
        _assert_istiod_metric(aggregator, metric)


@pytest.mark.skipif(ISTIO_MODE != "ambient", reason="Ambient-mode e2e: only runs on ambient envs")
def test_e2e_ambient(dd_agent_check, instance_openmetrics_v2):
    aggregator = dd_agent_check(instance_openmetrics_v2, rate=True)

    aggregator.assert_service_check('istio.openmetrics.health', Istio.OK)

    for metric in V2_ZTUNNEL_METRICS:
        aggregator.assert_metric(metric)

    for metric in V2_WAYPOINT_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    for metric in ISTIOD_V2_METRICS:
        if metric in INTERMITTENT_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric, at_least=0)
