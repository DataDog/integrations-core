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
