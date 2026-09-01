# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from datadog_checks.base.stubs import tagger
from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.strimzi.config_models import discovery
from datadog_checks.strimzi.config_models.discovery_strategies import from_strimzi_kube_container_name

DISCOVERY_ROLES: dict[str, tuple[str, int, str]] = {
    'strimzi-cluster-operator': ('cluster_operator_endpoint', 8080, 'http'),
    'topic-operator': ('topic_operator_endpoint', 8080, 'healthcheck'),
    'user-operator': ('user_operator_endpoint', 8081, 'healthcheck'),
}
DISCOVERY_ENDPOINT_FIELDS: frozenset[str] = frozenset(endpoint[0] for endpoint in DISCOVERY_ROLES.values())


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


def assert_candidate_endpoint(candidate: dict[str, Any], endpoint_field: str, host: str, port: int) -> None:
    instance = candidate['instances'][0]
    non_empty_endpoint_fields = {field for field in DISCOVERY_ENDPOINT_FIELDS if instance.get(field)}

    assert instance[endpoint_field] == f'http://{host}:{port}/metrics'
    assert non_empty_endpoint_fields == {endpoint_field}


@pytest.mark.parametrize(
    'tags',
    [
        pytest.param([], id='missing_kube_container_name'),
        pytest.param(['kube_container_name:tls-sidecar'], id='different_kube_container_name'),
        pytest.param(['pod_name:strimzi-cluster-operator'], id='no_container_name_tag'),
    ],
)
def test_from_strimzi_kube_container_name_ignores_missing_or_different_role_tags(tags: list[str]):
    tagger.set_tags({'container_id://abc': tags})
    service = build_service(ports=(Port(number=8080, name='http'),))

    assert list(from_strimzi_kube_container_name(service)) == []


@pytest.mark.parametrize(
    'service_id',
    [
        pytest.param('docker://abc', id='docker'),
        pytest.param('containerd://abc', id='containerd'),
        pytest.param('cri-o://abc', id='cri_o'),
        pytest.param('container_id://abc', id='container_id'),
    ],
)
def test_from_strimzi_kube_container_name_queries_tagger_container_entity(service_id: str):
    tagger.set_tags({'container_id://abc': ['kube_container_name:strimzi-cluster-operator']})
    service = build_service(service_id=service_id, ports=(Port(number=8080, name='http'),))

    assert list(from_strimzi_kube_container_name(service))
    tagger.assert_called('container_id://abc', tagger.LOW)


@pytest.mark.parametrize(
    'role,endpoint_field,port,port_name',
    [
        pytest.param('strimzi-cluster-operator', 'cluster_operator_endpoint', 8080, 'http', id='cluster_operator'),
        pytest.param('topic-operator', 'topic_operator_endpoint', 8080, 'healthcheck', id='topic_operator'),
        pytest.param('user-operator', 'user_operator_endpoint', 8081, 'healthcheck', id='user_operator'),
    ],
)
def test_generated_discovery_yields_correct_endpoint_per_role(
    role: str, endpoint_field: str, port: int, port_name: str
):
    tagger.set_tags({f'container_id://{role}': [f'kube_container_name:{role}']})
    service = build_service(service_id=f'docker://{role}', host='10.0.0.1', ports=(Port(number=port, name=port_name),))

    candidates = list(discovery.candidates(service))

    assert len(candidates) == 1
    assert_candidate_endpoint(candidates[0], endpoint_field, '10.0.0.1', port)


def test_generated_discovery_ignores_tls_sidecar_container():
    tagger.set_tags({'container_id://tls-sidecar': ['kube_container_name:tls-sidecar']})
    # The service exposes a port the operators would use, so only the tag mismatch can explain the result.
    service = build_service(
        service_id='docker://tls-sidecar', host='10.0.0.99', ports=(Port(number=8080, name='http'),)
    )

    assert list(discovery.candidates(service)) == []


@pytest.mark.parametrize(
    'ports',
    [
        pytest.param((Port(number=9090, name='metrics'),), id='port_with_other_name'),
        pytest.param((), id='no_ports'),
    ],
)
def test_from_strimzi_kube_container_name_yields_nothing_without_matching_port(ports: tuple[Port, ...]):
    tagger.set_tags({'container_id://abc': ['kube_container_name:strimzi-cluster-operator']})
    service = build_service(ports=ports)

    assert list(from_strimzi_kube_container_name(service)) == []


def test_from_strimzi_kube_container_name_picks_correct_port_when_multiple_present():
    tagger.set_tags({'container_id://abc': ['kube_container_name:topic-operator']})
    # Both http and healthcheck ports are present; strategy must pick healthcheck for topic-operator
    service = build_service(
        ports=(
            Port(number=8080, name='healthcheck'),
            Port(number=8081, name='http'),
        )
    )

    result = list(from_strimzi_kube_container_name(service))
    assert len(result) == 1
    assert result[0]['endpoints'].topic_operator_endpoint == 'http://10.0.0.1:8080/metrics'


def test_from_strimzi_kube_container_name_brackets_ipv6_host_in_url():
    tagger.set_tags({'container_id://abc': ['kube_container_name:strimzi-cluster-operator']})
    service = build_service(service_id='docker://abc', host='fd00::1', ports=(Port(number=8080, name='http'),))

    result = list(from_strimzi_kube_container_name(service))
    assert len(result) == 1
    assert result[0]['endpoints'].cluster_operator_endpoint == 'http://[fd00::1]:8080/metrics'
