# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ipaddress
from collections.abc import Iterable, Iterator
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

from .cache import Cache
from .filter import Filter


class Port(BaseModel):
    """An Autodiscovery-exposed port on a service."""

    model_config = ConfigDict(frozen=True)

    number: int
    name: str = ""


def _is_ipv6_literal(host: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(host), ipaddress.IPv6Address)
    except ValueError:
        return False


class Host(str):
    """A host that brackets IPv6 literals for URL templates; use ``!s`` when a template needs the raw value."""

    def __format__(self, format_spec: str) -> str:
        plain = str(self)  # plain copy: f'[{self}]' would recurse through __format__
        if not format_spec and _is_ipv6_literal(plain):
            return f'[{plain}]'
        return super().__format__(format_spec)


class Service(BaseModel):
    """An Autodiscovery-discovered service instance."""

    model_config = ConfigDict(frozen=True)

    id: str
    host: Annotated[str, AfterValidator(Host)]
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


def candidate_ports_by_name(service: Service, names: Iterable[str]) -> Iterator[Port]:
    """Yield ports matching each name in order, with no fallback to unmatched ports."""
    seen: set[int] = set()

    for name in dict.fromkeys(names):
        if not name:
            continue
        for port in service.ports:
            if port.name == name and port.number not in seen:
                seen.add(port.number)
                yield port
