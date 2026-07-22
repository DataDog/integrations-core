# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator

import pytest

from datadog_checks.base.stubs import tagger
from datadog_checks.base.utils.discovery import Service
from datadog_checks.traefik_mesh.config_models import discovery
from datadog_checks.traefik_mesh.config_models.discovery_strategies import from_traefik_mesh_kube_daemon_set


@pytest.fixture(autouse=True)
def reset_tagger() -> Iterator[None]:
    tagger.reset()
    yield
    tagger.reset()


def build_service(service_id: str = 'docker://abc', host: str = '10.0.0.1') -> Service:
    return Service(id=service_id, host=host, ports=())


def test_from_traefik_mesh_kube_daemon_set_yields_endpoint_on_matching_daemon_set() -> None:
    tagger.set_tags({'container_id://abc': ['kube_daemon_set:traefik-mesh-proxy']})

    contexts = list(from_traefik_mesh_kube_daemon_set(build_service(host='10.0.0.8')))

    assert len(contexts) == 1
    assert contexts[0]['endpoints'].openmetrics_endpoint == 'http://10.0.0.8:8080/metrics'
    assert contexts[0]['endpoints'].traefik_proxy_api_endpoint == 'http://10.0.0.8:8080'


@pytest.mark.parametrize(
    'tags',
    [
        pytest.param([], id='missing_kube_daemon_set'),
        # A plain, non-mesh Traefik reverse-proxy deployment runs the same image but is not the
        # Traefik Mesh proxy DaemonSet, so it must not be discovered.
        pytest.param(['kube_daemon_set:traefik'], id='different_daemon_set'),
        pytest.param(['kube_deployment:traefik-mesh-proxy'], id='deployment_not_daemon_set'),
        pytest.param(['pod_name:traefik-mesh-proxy-abcde'], id='no_workload_tag'),
    ],
)
def test_from_traefik_mesh_kube_daemon_set_ignores_missing_or_different_daemon_sets(tags: list[str]) -> None:
    tagger.set_tags({'container_id://abc': tags})

    assert list(from_traefik_mesh_kube_daemon_set(build_service())) == []


@pytest.mark.parametrize(
    'service_id',
    [
        pytest.param('docker://abc', id='docker'),
        pytest.param('containerd://abc', id='containerd'),
        pytest.param('cri-o://abc', id='cri_o'),
        pytest.param('container_id://abc', id='container_id'),
    ],
)
def test_from_traefik_mesh_kube_daemon_set_queries_tagger_container_entity(service_id: str) -> None:
    tagger.set_tags({'container_id://abc': ['kube_daemon_set:traefik-mesh-proxy']})

    assert len(list(from_traefik_mesh_kube_daemon_set(build_service(service_id=service_id)))) == 1
    tagger.assert_called('container_id://abc', tagger.LOW)


def test_generated_discovery_matches_on_daemon_set_tag() -> None:
    tagger.set_tags({'container_id://proxy': ['kube_daemon_set:traefik-mesh-proxy']})

    candidates = list(discovery.candidates(build_service(service_id='docker://proxy', host='10.0.0.5')))

    assert len(candidates) == 1
    instance = candidates[0]['instances'][0]
    assert instance['openmetrics_endpoint'] == 'http://10.0.0.5:8080/metrics'
    assert instance['traefik_proxy_api_endpoint'] == 'http://10.0.0.5:8080'


def test_generated_discovery_ignores_plain_traefik_deployment() -> None:
    tagger.set_tags({'container_id://traefik': ['kube_deployment:traefik']})

    assert list(discovery.candidates(build_service(service_id='docker://traefik', host='10.0.0.6'))) == []
