# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Port:
    """An Autodiscovery-exposed port on a service."""

    number: int
    name: str = ""


@dataclass(frozen=True)
class Service:
    """An Autodiscovery-discovered service instance."""

    id: str
    host: str
    ports: tuple[Port, ...] = field(default_factory=tuple)
