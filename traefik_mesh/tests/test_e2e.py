# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import pytest

from datadog_checks.base.stubs import tagger
from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.traefik_mesh import TraefikMeshCheck


def test_e2e_openmetrics_v2(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_service_check('traefik_mesh.openmetrics.health')
    aggregator.assert_service_check('traefik_mesh.controller.ready')


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(aggregator: Any, datadog_agent: Any) -> None:
    # The proxy's DaemonSet name (rather than its image, shared with plain Traefik deployments) is
    # what the discovery strategy keys on, so stub the tag the same way the real Agent's Kubernetes
    # tagger would derive it from the pod's DaemonSet owner reference.
    tagger.set_tags({'container_id://traefik-mesh-proxy': ['kube_daemon_set:traefik-mesh-proxy']})
    try:
        assert_all_discovery_candidates_stable_kubernetes(
            TraefikMeshCheck,
            aggregator,
            datadog_agent,
            namespace='traefik-mesh',
            pod_selector='component=maesh-mesh',
            service_id='docker://traefik-mesh-proxy',
        )
    finally:
        tagger.reset()


@pytest.mark.e2e
def test_e2e_discovery(aggregator: Any, datadog_agent: Any) -> None:
    aggregator = run_discovery_check_kubernetes(
        aggregator,
        datadog_agent,
        check_rate=True,
        discovery_min_instances=1,
        discovery_timeout=60,
    )

    aggregator.assert_service_check('traefik_mesh.openmetrics.health')
