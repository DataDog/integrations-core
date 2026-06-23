# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterable, Iterator

from pydantic import BaseModel, ConfigDict

from .cache import Cache
from .filter import Filter


class Port(BaseModel):
    """An Autodiscovery-exposed port on a service."""

    model_config = ConfigDict(frozen=True)

    number: int
    name: str = ""


class Service(BaseModel):
    """An Autodiscovery-discovered service instance."""

    model_config = ConfigDict(frozen=True)

    id: str
    host: str
    ports: tuple[Port, ...] = ()


class Discovery:
    def __init__(
        self,
        get_items_func,
        limit=None,
        include=None,
        exclude=None,
        interval=None,
        key=None,
    ):
        self._filter = Filter(limit, include, exclude, key)
        self._cache = Cache(get_items_func, interval)

    def get_items(self):
        items = self._cache.get_items()
        return self._filter.get_items(items)


def candidate_ports(service: Service, hints: Iterable[int]) -> Iterator[Port]:
    """Yield hinted ports first, then remaining service ports."""
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
    """Yield a ``{'port': Port}`` render context per candidate port."""
    for port in candidate_ports(service, port_hints):
        yield {'port': port}
