# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Iterable, Iterator
from types import SimpleNamespace
from typing import Any

from datadog_checks.base.utils.discovery import Service, candidate_ports_by_name, discovery_strategy
from datadog_checks.base.utils.tagging import tagger


def container_tagger_entity_id(container_id: str) -> str:
    """Return the tagger entity ID for a Kubernetes container runtime ID."""
    if container_id and '://' in container_id:
        return '://'.join(('container_id', container_id.split('://', 1)[1]))
    return container_id


def tag_value(tags: Iterable[str], name: str) -> str | None:
    prefix = f'{name}:'
    for tag in tags:
        if tag.startswith(prefix):
            return tag.removeprefix(prefix)

    return None


@discovery_strategy(provides=('instance',))
def from_kubevirt_handler_named_metrics_port(service: Service) -> Iterator[dict[str, Any]]:
    tags = tagger.tag(container_tagger_entity_id(service.id), tagger.ORCHESTRATOR) or []
    kube_namespace = tag_value(tags, 'kube_namespace')
    pod_name = tag_value(tags, 'pod_name')
    if not kube_namespace or not pod_name:
        return

    for port in candidate_ports_by_name(service, ['metrics']):
        yield {
            'instance': SimpleNamespace(
                metrics_endpoint=f'https://{service.host}:{port.number}/metrics',
                healthz_endpoint=f'https://{service.host}:{port.number}/healthz',
                kube_namespace=kube_namespace,
                kube_pod_name=pod_name,
            )
        }
