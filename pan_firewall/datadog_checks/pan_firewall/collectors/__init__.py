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
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, cast
from xml.etree.ElementTree import Element

from datadog_checks.base.log import CheckLoggingAdapter

if TYPE_CHECKING:
    from ..api import PanosClient
    from ..config_models.instance import InstanceConfig
    from ..identity import DeviceIdentity


class FirewallLog(CheckLoggingAdapter):
    """The check's log with `pan_firewall <firewall>: ` in front of every message, so a warning names its firewall."""

    def __init__(self, log: CheckLoggingAdapter, firewall: str):
        super().__init__(log.logger, log.check_id)
        self._prefix = f'pan_firewall {firewall}: '

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        return super().process(f'{self._prefix}{msg}', kwargs)


class Sample(NamedTuple):
    name: str  # without prefix, e.g. 'bgp.peer.status'
    value: float
    tags: tuple[str, ...]  # collector-specific tags only
    kind: Literal['gauge', 'monotonic_count', 'count']


@dataclass(frozen=True)
class Watermark:
    """Where the threat collector resumes: the `seqno` of the last log counted, and the last `seqno` reset check.

    `last_reset_check` is a reading of the schedule's monotonic clock, so it means nothing after a restart: the
    reset check treats a value ahead of the clock as due. `updated` is the wall-clock time the watermark was written,
    which still means something after a restart.
    """

    seqno: int
    last_reset_check: float
    updated: float

    def to_json(self) -> str:
        return json.dumps({'seqno': self.seqno, 'last_reset_check': self.last_reset_check, 'updated': self.updated})

    @classmethod
    def from_json(cls, raw: str) -> Watermark:
        """Load a watermark written by `to_json()`. Raises ValueError, TypeError or KeyError for anything else,
        including a watermark without `updated`."""
        data = json.loads(raw)
        return cls(
            seqno=int(data['seqno']),
            last_reset_check=float(data['last_reset_check']),
            updated=float(data['updated']),
        )


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
class ReportJob:
    """A report job still running when a run ended: the report it belongs to and how many runs it has been carried."""

    report: str
    job_id: str
    carries: int = 1


@dataclass
class ReportState:
    pending: ReportJob | None = None  # polled first next run, never submitted again
    cursor: int = 0  # index in `REPORTS` of the next report to submit; back to 0 once a cycle of all of them is done


@dataclass
class FirewallState:
    """What the poller keeps about one firewall between runs. Later collectors add their own fields."""

    # `show interface all`: the `result/ifnet/entry` rows, and the `result/hw/entry` rows by interface name. Both
    # keep their last value when the call fails; `interface_map` is None until the call first answers.
    interface_rows: list[Element] = field(default_factory=list)
    interface_map: dict[str, Element] | None = None
    vsys: list[str] = field(default_factory=lambda: ['vsys1'])
    ha_state: str | None = None
    # Written by `vpn`, read by `interfaces` (which owns the `counter interface all` call): the tags of each IPSec
    # tunnel by its `tunnel.N` interface, None until `vpn` first answers, and the raw `show vpn flow` state by interface.
    tunnel_tags: dict[str, tuple[str, ...]] | None = None
    tunnel_states: dict[str, str] = field(default_factory=dict)
    threats: ThreatState = field(default_factory=ThreatState)
    # Keys of the warnings already logged for this firewall (see `warn_once`): a condition that lasts is warned about
    # once, not once per run.
    warned: set[str] = field(default_factory=set)
    reports: ReportState = field(default_factory=ReportState)
    # Collectors that ran but must stay due, as a job of theirs is still running: the poller leaves them out of
    # `mark_run`, so they run again next run instead of after their interval.
    still_due: set[str] = field(default_factory=set)


@dataclass
class CollectContext:
    client: PanosClient
    identity: DeviceIdentity
    state: FirewallState  # interface map, vpn cache, pending jobs, watermark, ha_state
    config: InstanceConfig
    log: CheckLoggingAdapter
    # `state.tunnel_tags` as it was when the run started: what `interfaces` tags the tunnel counters with, so that
    # whether they are sent does not depend on which of the parallel collectors finishes first.
    tunnel_tags: dict[str, tuple[str, ...]] | None = None
    # The schedule's monotonic clock, the wall clock, and the check's persistent cache (read returns '' for an unknown
    # key).
    clock: Callable[[], float] = time.monotonic
    wall_clock: Callable[[], float] = time.time
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


def warn_once(ctx: CollectContext, key: str, msg: str, *args: object) -> None:
    """Log the warning the first time `key` is seen for this firewall, and at debug level after that."""
    if key in ctx.state.warned:
        ctx.log.debug(msg, *args)
        return
    ctx.state.warned.add(key)
    ctx.log.warning(msg, *args)


class _OnceLog:
    """A logger whose `warning` is `warn_once` keyed by the formatted message; everything else is the context's log."""

    def __init__(self, ctx: CollectContext):
        self._ctx = ctx

    def warning(self, msg: str, *args: object) -> None:
        warn_once(self._ctx, msg % args if args else msg, msg, *args)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ctx.log, name)


def once_log(ctx: CollectContext) -> CheckLoggingAdapter:
    """The context's log for the `parse_*` functions, which warn about an unknown shape: once per firewall."""
    return cast('CheckLoggingAdapter', _OnceLog(ctx))
