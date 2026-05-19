# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Port:
    number: int
    name: str = ""


@dataclass(frozen=True)
class Service:
    id: str
    host: str
    ports: tuple[Port, ...] = field(default_factory=tuple)

    @property
    def url_host(self) -> str:
        """Host string safe for use in a URL. Brackets bare IPv6 literals."""
        if ':' in self.host and not self.host.startswith('['):
            return f'[{self.host}]'
        return self.host
