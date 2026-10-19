# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from datadog_checks.base.utils.discovery import Service, candidate_ports_by_name, discovery_strategy
from datadog_checks.base.utils.tagging import tagger

STRIMZI_ROLE_PORTS: dict[str, tuple[str, str]] = {
    'strimzi-cluster-operator': ('cluster_operator_endpoint', 'http'),
    'topic-operator': ('topic_operator_endpoint', 'healthcheck'),
    'user-operator': ('user_operator_endpoint', 'healthcheck'),
}


@dataclass(frozen=True)
class StrimziDiscoveryEndpoints:
    cluster_operator_endpoint: str = ''
    topic_operator_endpoint: str = ''
    user_operator_endpoint: str = ''


def container_tagger_entity_id(container_id: str) -> str:
    """Return the tagger entity ID for a Kubernetes container runtime ID."""
    if container_id and '://' in container_id:
        return '://'.join(('container_id', container_id.split('://', 1)[1]))

    return container_id


@discovery_strategy(provides=('endpoints',))
def from_strimzi_kube_container_name(service: Service) -> Iterator[dict[str, StrimziDiscoveryEndpoints]]:
    """Yield the role-specific metrics endpoint for a matching Strimzi container.

    All three Strimzi operator roles (Cluster Operator, Topic Operator, User Operator) share the
    same container image (``quay.io/strimzi/operator``), and the Topic Operator and User Operator
    even share the same pod. Each role runs as a distinct container with a unique
    ``kube_container_name`` tag, so a single tagger lookup is enough to identify which role is
    present.
    """
    tags = tagger.tag(container_tagger_entity_id(service.id), tagger.LOW) or []
    for kube_container_name, (endpoint_field, port_name) in STRIMZI_ROLE_PORTS.items():
        if f'kube_container_name:{kube_container_name}' not in tags:
            continue

        for port in candidate_ports_by_name(service, [port_name]):
            endpoint = f'http://{service.host}:{port.number}/metrics'
            yield {'endpoints': StrimziDiscoveryEndpoints(**{endpoint_field: endpoint})}
            return

        # A container can only have one kube_container_name, so once we've matched a
        # role we're done — break from the outer loop regardless of port resolution.
        return
