# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from datadog_checks.base.utils.discovery import Service, discovery_strategy
from datadog_checks.base.utils.tagging import tagger

ARGOCD_ROLE_ENDPOINTS = {
    'argocd-application-controller': ('app_controller_endpoint', 8082),
    'argocd-applicationset-controller': ('appset_controller_endpoint', 8080),
    'argocd-server': ('api_server_endpoint', 8083),
    'argocd-repo-server': ('repo_server_endpoint', 8084),
    'argocd-notifications-controller': ('notifications_controller_endpoint', 9001),
    'argocd-commit-server': ('commit_server_endpoint', 8087),
}


@dataclass(frozen=True)
class ArgoCDDiscoveryEndpoints:
    app_controller_endpoint: str = ''
    appset_controller_endpoint: str = ''
    api_server_endpoint: str = ''
    repo_server_endpoint: str = ''
    notifications_controller_endpoint: str = ''
    commit_server_endpoint: str = ''


def container_tagger_entity_id(container_id: str) -> str:
    """Return the tagger entity ID for a Kubernetes container runtime ID."""
    if container_id and '://' in container_id:
        return '://'.join(('container_id', container_id.split('://', 1)[1]))

    return container_id


@discovery_strategy(provides=('endpoints',))
def from_argocd_kube_app_name(service: Service) -> Iterator[dict[str, ArgoCDDiscoveryEndpoints]]:
    """Yield the role-specific metrics endpoint for a matching Argo CD container."""
    tags = tagger.tag(container_tagger_entity_id(service.id), tagger.LOW) or []
    for kube_app_name, (endpoint_field, port) in ARGOCD_ROLE_ENDPOINTS.items():
        if f'kube_app_name:{kube_app_name}' not in tags:
            continue

        endpoint = f'http://{service.host}:{port}/metrics'
        yield {'endpoints': ArgoCDDiscoveryEndpoints(**{endpoint_field: endpoint})}
        return
