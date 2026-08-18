# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from datadog_checks.base.utils.discovery import Service, discovery_strategy


@discovery_strategy(provides=('port',))
def from_named_ports(service: Service, port_names: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Yield named service ports in requested order without duplicate port numbers."""
    seen: set[int] = set()

    for name in dict.fromkeys(port_names):
        if not name:
            continue
        for port in service.ports:
            if port.name == name and port.number not in seen:
                seen.add(port.number)
                yield {'port': port}
