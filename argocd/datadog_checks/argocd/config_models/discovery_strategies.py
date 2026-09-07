# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can define custom (local:) discovery strategies for this integration.
# Decorate a generator with @discovery_strategy (imported from
# datadog_checks.base.utils.discovery) and reference it from the spec discovery
# stanza as `strategy: local:<function_name>`. The function receives the
# discovered Service plus the inputs declared in the spec and yields one context
# (ctx) mapping per candidate, exposing the keys listed in `provides`.

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from datadog_checks.base.utils.discovery import Service, candidate_ports_by_name, discovery_strategy
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
    """Yield the role-specific metrics endpoint for a matching Argo CD container.

    All Argo CD roles share the ``quay.io/argoproj/argocd`` image, so the role is identified
    by the ``kube_app_name`` tag (from the ``app.kubernetes.io/name`` label). The official
    install manifest names the ``metrics`` port only on the applicationset-controller, so a
    declared ``metrics`` port is preferred when present and the role's default metrics port
    is used as the fallback for the unnamed or undeclared ports of the other roles.
    """
    tags = tagger.tag(container_tagger_entity_id(service.id), tagger.LOW) or []
    for kube_app_name, (endpoint_field, default_port) in ARGOCD_ROLE_ENDPOINTS.items():
        if f'kube_app_name:{kube_app_name}' not in tags:
            continue

        port = next(candidate_ports_by_name(service, ['metrics']), None)
        port_number = port.number if port is not None else default_port
        endpoint = f'http://{service.host}:{port_number}/metrics'
        yield {'endpoints': ArgoCDDiscoveryEndpoints(**{endpoint_field: endpoint})}
        return
