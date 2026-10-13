# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared types of the collectors, and the registry the poller runs them from.

A collector is a plain function `collect(ctx) -> list[Sample]`, registered in COLLECT_FUNCTIONS under its name in
`constants.COLLECTORS`.
"""

from __future__ import annotations

import json
import time
from collections import Counter
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


@dataclass(frozen=True)
class Watermark:
    """Where the threat collector resumes: the `seqno` of the last log counted, and the last `seqno` reset check.

    `last_reset_check` is a reading of the schedule's monotonic clock, so it means nothing after a restart: the
    reset check treats a value ahead of the clock as due.
    """

    seqno: int
    last_reset_check: float

    def to_json(self) -> str:
        return json.dumps({'seqno': self.seqno, 'last_reset_check': self.last_reset_check})

    @classmethod
    def from_json(cls, raw: str) -> Watermark:
        """Load a watermark written by `to_json()`. Raises ValueError, TypeError or KeyError for anything else."""
        data = json.loads(raw)
        return cls(seqno=int(data['seqno']), last_reset_check=float(data['last_reset_check']))


@dataclass
class ThreatJob:
    """A threat log job, and what the pass it belongs to has gathered so far.

    `purpose` is `baseline` (first run: newest log), `forward` (logs above `base_seqno`, page after page) or `reset`
    (newest log, to detect a `seqno` reset). `job_id` is None until the job is submitted.
    """

    purpose: Literal['baseline', 'forward', 'reset']
    base_seqno: int = 0
    page_size: int = 1
    skip: int = 0
    job_id: str | None = None
    page_entries: int = 0
    newest_seqno: int | None = None
    counted: int = 0
    counts: Counter[tuple[str, str, str, str]] = field(default_factory=Counter)


@dataclass
class ThreatState:
    watermark: Watermark | None = None
    loaded: bool = False  # the watermark has been read from the persistent cache
    pending: ThreatJob | None = None  # a job still running when the last run ended, polled first next run


@dataclass
class FirewallState:
    """What the poller keeps about one firewall between runs. Later collectors add their own fields."""

    # `show interface all`: the `result/ifnet/entry` rows, and the `result/hw/entry` rows by interface name. Both
    # keep their last value when the call fails; `interface_map` is None until the call first answers.
    interface_rows: list[Element] = field(default_factory=list)
    interface_map: dict[str, Element] | None = None
    vsys: list[str] = field(default_factory=lambda: ['vsys1'])
    ha_state: str | None = None
    # The routing engine warning (advanced routing on) is logged once per firewall, not once per run.
    are_warned: bool = False
    # Written by `vpn`, read by `interfaces` (which owns the `counter interface all` call): the tags of each IPSec
    # tunnel by its `tunnel.N` interface, None until `vpn` first answers, and the raw `show vpn flow` state by interface.
    tunnel_tags: dict[str, tuple[str, ...]] | None = None
    tunnel_states: dict[str, str] = field(default_factory=dict)
    threats: ThreatState = field(default_factory=ThreatState)
    # Warnings logged once per firewall instead of once per run: the HA link counters, and the power sensors whose
    # alarm has no direction (keyed by slot and sensor name).
    ha_warned: bool = False
    warned_sensors: set[str] = field(default_factory=set)


@dataclass
class CollectContext:
    client: PanosClient
    identity: DeviceIdentity
    state: FirewallState  # interface map, vpn cache, pending jobs, watermark, ha_state
    config: InstanceConfig
    log: CheckLoggingAdapter
    # The schedule's monotonic clock, and the check's persistent cache (read returns '' for an unknown key).
    clock: Callable[[], float] = time.monotonic
    read_cache: Callable[[str], str] = lambda key: ''
    write_cache: Callable[[str, str], None] = lambda key, value: None


Collector = Callable[[CollectContext], list[Sample]]

# Collector name -> function, filled by `@register(name)` when the collector module is imported.
COLLECT_FUNCTIONS: dict[str, Collector] = {}


def register(name: str) -> Callable[[Collector], Collector]:
    """Register the decorated function as the collector `name`. The module defining it must be imported by `poller`."""

    def decorator(function: Collector) -> Collector:
        COLLECT_FUNCTIONS[name] = function
        return function

    return decorator
