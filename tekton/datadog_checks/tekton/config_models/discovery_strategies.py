# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can define custom (local:) discovery strategies for this integration.
#
# Decorate a generator with @discovery_strategy (imported from
# datadog_checks.base.utils.discovery) and reference it from the spec discovery
# stanza as `strategy: local:<function_name>`. The function receives the
# discovered Service plus the inputs declared in the spec and yields one context
# (ctx) mapping per candidate, exposing the keys listed in `provides`.
#
# from datadog_checks.base.utils.discovery import discovery_strategy
#
# @discovery_strategy(provides=('svc',))
# def from_some_config(service, config_path):
#     ...
#     yield {'svc': ...}

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from datadog_checks.base.utils.discovery import Port, Service, candidate_ports_by_name, discovery_strategy
from datadog_checks.base.utils.tagging import tagger

TEKTON_CONTROLLERS: dict[str, tuple[str, int]] = {
    'tekton-pipelines-controller': ('pipelines_controller_endpoint', 9090),
    'tekton-triggers-controller': ('triggers_controller_endpoint', 9000),
}


@dataclass(frozen=True)
class TektonDiscoveryEndpoints:
    pipelines_controller_endpoint: str = ''
    triggers_controller_endpoint: str = ''


def container_tagger_entity_id(container_id: str) -> str:
    """Return the tagger entity ID for a Kubernetes container runtime ID."""
    if container_id and '://' in container_id:
        return '://'.join(('container_id', container_id.split('://', 1)[1]))

    return container_id


@discovery_strategy(provides=('endpoints',))
def from_tekton_kube_container_name(service: Service) -> Iterator[dict[str, TektonDiscoveryEndpoints]]:
    """Yield the controller-specific metrics endpoint for a matching Tekton controller container."""
    tags = tagger.tag(container_tagger_entity_id(service.id), tagger.LOW) or []
    for container_name, (endpoint_field, default_port) in TEKTON_CONTROLLERS.items():
        if f'kube_container_name:{container_name}' not in tags:
            continue

        port = next(candidate_ports_by_name(service, ['metrics']), None) or Port(number=default_port)
        endpoint = f'http://{service.host}:{port.number}/metrics'
        yield {'endpoints': TektonDiscoveryEndpoints(**{endpoint_field: endpoint})}
        return
