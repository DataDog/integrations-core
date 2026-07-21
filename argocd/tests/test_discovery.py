# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from datadog_checks.argocd.config_models import discovery
from datadog_checks.argocd.config_models.discovery_strategies import from_argocd_kube_app_name
from datadog_checks.base.stubs import tagger
from datadog_checks.base.utils.discovery import Service

KIND_MANIFEST = Path(__file__).parent / 'kind' / 'argocd_install.yaml'
DISCOVERY_ROLE_ENDPOINTS: dict[str, tuple[str, int]] = {
    'argocd-application-controller': ('app_controller_endpoint', 8082),
    'argocd-applicationset-controller': ('appset_controller_endpoint', 8080),
    'argocd-server': ('api_server_endpoint', 8083),
    'argocd-repo-server': ('repo_server_endpoint', 8084),
    'argocd-notifications-controller': ('notifications_controller_endpoint', 9001),
    'argocd-commit-server': ('commit_server_endpoint', 8087),
}
KIND_DISCOVERY_ROLE_ENDPOINTS: dict[str, tuple[str, int]] = {
    role: endpoint for role, endpoint in DISCOVERY_ROLE_ENDPOINTS.items() if role != 'argocd-commit-server'
}
DISCOVERY_ENDPOINT_FIELDS: frozenset[str] = frozenset(endpoint[0] for endpoint in DISCOVERY_ROLE_ENDPOINTS.values())


@pytest.fixture(autouse=True)
def reset_tagger() -> Iterator[None]:
    tagger.reset()
    yield
    tagger.reset()


def build_service(service_id: str = 'docker://abc', host: str = '10.0.0.1') -> Service:
    return Service(id=service_id, host=host, ports=())


def kind_workload_app_names() -> set[str]:
    app_names: set[str] = set()
    with KIND_MANIFEST.open(encoding='utf-8') as f:
        for manifest in yaml.safe_load_all(f):
            if not isinstance(manifest, dict) or manifest.get('kind') not in {'Deployment', 'StatefulSet'}:
                continue

            spec = manifest.get('spec', {})
            if not isinstance(spec, dict):
                continue

            template = spec.get('template', {})
            if not isinstance(template, dict):
                continue

            metadata = template.get('metadata', {})
            if not isinstance(metadata, dict):
                continue

            labels = metadata.get('labels', {})
            if not isinstance(labels, dict):
                continue

            app_name = labels.get('app.kubernetes.io/name')
            if isinstance(app_name, str):
                app_names.add(app_name)

    return app_names


def assert_candidate_endpoint(candidate: dict[str, Any], endpoint_field: str, host: str, port: int) -> None:
    instance = candidate['instances'][0]
    non_empty_endpoint_fields = {field for field in DISCOVERY_ENDPOINT_FIELDS if instance.get(field)}

    assert instance[endpoint_field] == f'http://{host}:{port}/metrics'
    assert non_empty_endpoint_fields == {endpoint_field}


def test_from_argocd_kube_app_name_yields_role_endpoint_on_matching_role() -> None:
    tagger.set_tags({'container_id://abc': ['kube_app_name:argocd-server']})

    contexts = list(from_argocd_kube_app_name(build_service(host='10.0.0.8')))

    assert len(contexts) == 1
    assert contexts[0]['endpoints'].api_server_endpoint == 'http://10.0.0.8:8083/metrics'


@pytest.mark.parametrize(
    'tags',
    [
        pytest.param([], id='missing_kube_app_name'),
        pytest.param(['kube_app_name:argocd-redis'], id='different_kube_app_name'),
        pytest.param(['pod_name:argocd-server'], id='no_role_tag'),
    ],
)
def test_from_argocd_kube_app_name_ignores_missing_or_different_role_tags(tags: list[str]) -> None:
    tagger.set_tags({'container_id://abc': tags})

    assert list(from_argocd_kube_app_name(build_service())) == []


@pytest.mark.parametrize(
    'service_id',
    [
        pytest.param('docker://abc', id='docker'),
        pytest.param('containerd://abc', id='containerd'),
        pytest.param('cri-o://abc', id='cri_o'),
        pytest.param('container_id://abc', id='container_id'),
    ],
)
def test_from_argocd_kube_app_name_queries_tagger_container_entity(service_id: str) -> None:
    tagger.set_tags({'container_id://abc': ['kube_app_name:argocd-server']})

    assert len(list(from_argocd_kube_app_name(build_service(service_id=service_id)))) == 1
    tagger.assert_called('container_id://abc', tagger.LOW)


def test_generated_discovery_matches_kind_fixture_roles() -> None:
    app_names = kind_workload_app_names()
    assert set(KIND_DISCOVERY_ROLE_ENDPOINTS) <= app_names

    tagger.set_tags({f'container_id://{role}': [f'kube_app_name:{role}'] for role in KIND_DISCOVERY_ROLE_ENDPOINTS})

    for index, (role, (endpoint_field, port)) in enumerate(KIND_DISCOVERY_ROLE_ENDPOINTS.items(), 1):
        host = f'10.0.0.{index}'
        candidates = list(discovery.candidates(build_service(service_id=f'docker://{role}', host=host)))

        assert len(candidates) == 1
        assert_candidate_endpoint(candidates[0], endpoint_field, host, port)


def test_generated_discovery_notifications_uses_fixed_port_without_declared_port() -> None:
    tagger.set_tags({'container_id://notifications': ['kube_app_name:argocd-notifications-controller']})

    candidates = list(discovery.candidates(build_service(service_id='docker://notifications', host='10.0.0.50')))

    assert len(candidates) == 1
    assert_candidate_endpoint(candidates[0], 'notifications_controller_endpoint', '10.0.0.50', 9001)


def test_generated_discovery_supports_commit_server_synthetically() -> None:
    tagger.set_tags({'container_id://commit-server': ['kube_app_name:argocd-commit-server']})

    candidates = list(discovery.candidates(build_service(service_id='docker://commit-server', host='10.0.0.60')))

    assert len(candidates) == 1
    assert_candidate_endpoint(candidates[0], 'commit_server_endpoint', '10.0.0.60', 8087)


def test_generated_discovery_ignores_kind_redis_workload() -> None:
    assert 'argocd-redis' in kind_workload_app_names()
    tagger.set_tags({'container_id://redis': ['kube_app_name:argocd-redis']})

    assert list(discovery.candidates(build_service(service_id='docker://redis', host='10.0.0.70'))) == []
