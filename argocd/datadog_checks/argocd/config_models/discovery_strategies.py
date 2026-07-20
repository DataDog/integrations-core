# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Iterator

from datadog_checks.base.utils.discovery import Port, Service, discovery_strategy
from datadog_checks.base.utils.tagging import tagger


def container_tagger_entity_id(container_id: str) -> str:
    """Return the tagger entity ID for a Kubernetes container runtime ID."""
    if container_id and '://' in container_id:
        return '://'.join(('container_id', container_id.split('://', 1)[1]))

    return container_id


@discovery_strategy(provides=('port',))
def from_kube_app_name(service: Service, kube_app_name: str, port: int) -> Iterator[dict[str, Port]]:
    """Yield a fixed metrics port when the container role tag matches."""
    tags = tagger.tag(container_tagger_entity_id(service.id), tagger.LOW) or []
    if f'kube_app_name:{kube_app_name}' in tags:
        yield {'port': Port(number=port)}
