# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterable, Iterator

from .service import Port, Service


def candidate_ports(service: Service, hints: Iterable[int]) -> Iterator[Port]:
    """Yield ports in discovery order: hinted ports first (in hint order), then remaining service ports.

    Hints not exposed by the service are silently skipped. Duplicate port numbers are collapsed
    so each port appears at most once.
    """
    by_number = {port.number: port for port in service.ports}
    seen: set[int] = set()

    for hint in hints:
        if hint in by_number and hint not in seen:
            seen.add(hint)
            yield by_number[hint]

    for port in service.ports:
        if port.number not in seen:
            seen.add(port.number)
            yield port


def from_ports(service: Service, *, port_hints: Iterable[int]) -> Iterator[dict[str, Port]]:
    """Yield a ``{'port': Port}`` render context per candidate port, in ``candidate_ports`` order."""
    for port in candidate_ports(service, port_hints):
        yield {'port': port}
