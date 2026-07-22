# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from datadog_checks.base.utils.discovery import Service, discovery_strategy
from datadog_checks.base.utils.tagging import tagger

TRAEFIK_MESH_PROXY_DAEMON_SET = 'traefik-mesh-proxy'
TRAEFIK_MESH_PROXY_METRICS_PORT = 8080


@dataclass(frozen=True)
class TraefikMeshDiscoveryEndpoints:
    openmetrics_endpoint: str = ''
    traefik_proxy_api_endpoint: str = ''


def container_tagger_entity_id(container_id: str) -> str:
    """Return the tagger entity ID for a Kubernetes container runtime ID."""
    if container_id and '://' in container_id:
        return '://'.join(('container_id', container_id.split('://', 1)[1]))

    return container_id


@discovery_strategy(provides=('endpoints',))
def from_traefik_mesh_kube_daemon_set(service: Service) -> Iterator[dict[str, TraefikMeshDiscoveryEndpoints]]:
    """Yield the proxy's metrics/API endpoint for a matching Traefik Mesh proxy container.

    The proxy runs the stock upstream ``traefik`` image, which is indistinguishable from a plain
    (non-mesh) Traefik reverse-proxy deployment at the image level. The Traefik Mesh Helm chart
    hardcodes the proxy's DaemonSet name to ``traefik-mesh-proxy`` though, so gating on that
    Kubernetes-derived tag (rather than the image) avoids matching an unrelated Traefik deployment.
    """
    tags = tagger.tag(container_tagger_entity_id(service.id), tagger.LOW) or []
    if f'kube_daemon_set:{TRAEFIK_MESH_PROXY_DAEMON_SET}' not in tags:
        return

    base_url = f'http://{service.host}:{TRAEFIK_MESH_PROXY_METRICS_PORT}'
    yield {
        'endpoints': TraefikMeshDiscoveryEndpoints(
            openmetrics_endpoint=f'{base_url}/metrics',
            traefik_proxy_api_endpoint=base_url,
        )
    }
