# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterable, Iterator

from .service import Port, Service


def candidate_ports(service: Service, hints: Iterable[int]) -> Iterator[Port]:
    """Yield ports to probe for a service, hint-first then remaining.

    Hints are always yielded (with the port name from the service when known,
    or an empty name when only declared via a docker-compose mapping that
    doesn't reach the EXPOSE list). Duplicates are collapsed.
    """
    by_number = {p.number: p for p in service.ports}
    seen: set[int] = set()
    for h in hints:
        if h not in seen:
            seen.add(h)
            yield by_number.get(h) or Port(number=h)
    for p in service.ports:
        if p.number not in seen:
            seen.add(p.number)
            yield p
