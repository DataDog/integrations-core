# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared types of the collectors, and the registry the poller runs them from.

A collector is a plain function `collect(ctx) -> list[Sample]`, registered in COLLECT_FUNCTIONS under its name in
`constants.COLLECTORS`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, NamedTuple
from xml.etree.ElementTree import Element

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

    from ..api import PanosClient
    from ..config_models.instance import InstanceConfig
    from ..identity import DeviceIdentity


class Sample(NamedTuple):
    name: str  # without prefix, e.g. 'bgp.peer.status'
    value: float
    tags: tuple[str, ...]  # collector-specific tags only
    kind: Literal['gauge', 'monotonic_count', 'count']


@dataclass
class FirewallState:
    """What the poller keeps about one firewall between runs. Later collectors add their own fields."""

    # `show interface all`: the `result/ifnet/entry` rows, and the `result/hw/entry` rows by interface name. Both
    # keep their last value when the call fails; `interface_map` is None until the call first answers.
    interface_rows: list[Element] = field(default_factory=list)
    interface_map: dict[str, Element] | None = None
    vsys: list[str] = field(default_factory=lambda: ['vsys1'])
    ha_state: str | None = None


@dataclass
class CollectContext:
    client: PanosClient
    identity: DeviceIdentity
    state: FirewallState  # interface map, vpn cache, pending jobs, watermark, ha_state
    config: InstanceConfig
    log: CheckLoggingAdapter


Collector = Callable[[CollectContext], list[Sample]]

# Collector name -> function, filled by `@register(name)` when the collector module is imported.
COLLECT_FUNCTIONS: dict[str, Collector] = {}


def register(name: str) -> Callable[[Collector], Collector]:
    """Register the decorated function as the collector `name`. The module defining it must be imported by `poller`."""

    def decorator(function: Collector) -> Collector:
        COLLECT_FUNCTIONS[name] = function
        return function

    return decorator
