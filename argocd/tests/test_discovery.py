# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from datadog_checks.argocd.config_models import discovery
from datadog_checks.argocd.config_models.discovery_strategies import from_argocd_kube_app_name
from datadog_checks.base.stubs import tagger
from datadog_checks.base.utils.discovery import Port, Service

DISCOVERY_ROLES = (
    ('argocd-application-controller', 'app_controller_endpoint', 8082),
    ('argocd-applicationset-controller', 'appset_controller_endpoint', 8080),
    ('argocd-server', 'api_server_endpoint', 8083),
    ('argocd-repo-server', 'repo_server_endpoint', 8084),
    ('argocd-notifications-controller', 'notifications_controller_endpoint', 9001),
    ('argocd-commit-server', 'commit_server_endpoint', 8087),
)
DISCOVERY_ENDPOINT_FIELDS = frozenset(endpoint_field for _, endpoint_field, _ in DISCOVERY_ROLES)


@pytest.fixture(autouse=True)
def reset_tagger() -> Iterator[None]:
    tagger.reset()
    yield
    tagger.reset()


def build_service(
    service_id: str = 'docker://abc',
    host: str = '10.0.0.1',
    ports: tuple[Port, ...] = (),
) -> Service:
    return Service(id=service_id, host=host, ports=ports)


def assert_candidate_endpoint(candidate: dict[str, Any], endpoint_field: str, endpoint: str) -> None:
    instance = candidate['instances'][0]

    assert instance[endpoint_field] == endpoint
    assert {field for field in DISCOVERY_ENDPOINT_FIELDS if instance.get(field)} == {endpoint_field}


@pytest.mark.parametrize(
    'role,endpoint_field,port',
    [pytest.param(*role, id=role[0].removeprefix('argocd-')) for role in DISCOVERY_ROLES],
)
def test_generated_discovery_yields_role_endpoint(role: str, endpoint_field: str, port: int):
    tagger.set_tags({f'container_id://{role}': [f'kube_app_name:{role}']})
    service = build_service(service_id=f'containerd://{role}')

    candidates = list(discovery.candidates(service))

    assert len(candidates) == 1
    assert_candidate_endpoint(candidates[0], endpoint_field, f'http://10.0.0.1:{port}/metrics')


@pytest.mark.parametrize(
    'ports,expected_port',
    [
        pytest.param((Port(number=9999, name='metrics'),), 9999, id='named_metrics_port'),
        pytest.param((Port(number=8080), Port(number=8083)), 8083, id='default_port'),
    ],
)
def test_discovery_selects_metrics_port(ports: tuple[Port, ...], expected_port: int):
    tagger.set_tags({'container_id://abc': ['kube_app_name:argocd-server']})

    contexts = list(from_argocd_kube_app_name(build_service(ports=ports)))

    assert len(contexts) == 1
    assert contexts[0]['endpoints'].api_server_endpoint == f'http://10.0.0.1:{expected_port}/metrics'


def test_discovery_brackets_ipv6_host():
    tagger.set_tags({'container_id://abc': ['kube_app_name:argocd-server']})

    contexts = list(from_argocd_kube_app_name(build_service(host='fd00::1')))

    assert len(contexts) == 1
    assert contexts[0]['endpoints'].api_server_endpoint == 'http://[fd00::1]:8083/metrics'


@pytest.mark.parametrize(
    'tags',
    [
        pytest.param([], id='missing_role'),
        pytest.param(['kube_app_name:argocd-redis'], id='unsupported_role'),
        pytest.param(['pod_name:argocd-server'], id='unrelated_tag'),
        pytest.param(
            ['kube_app_name:argocd-repo-server', 'kube_container_name:copyutil'],
            id='copyutil_init_container',
        ),
    ],
)
def test_generated_discovery_ignores_non_role_containers(tags: list[str]):
    tagger.set_tags({'container_id://abc': tags})

    assert list(discovery.candidates(build_service())) == []
