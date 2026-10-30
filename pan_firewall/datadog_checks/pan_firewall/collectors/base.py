# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared types of the collectors: a collector is a function `collect(ctx) -> list[Sample]`."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, NamedTuple
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.errors import PanosAuthError, PanosError, PanosUnreachable
from datadog_checks.pan_firewall.log_utils import warn_once

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter
    from datadog_checks.pan_firewall.api import PanosClient
    from datadog_checks.pan_firewall.config_models.instance import InstanceConfig
    from datadog_checks.pan_firewall.identity import DeviceIdentity
    from datadog_checks.pan_firewall.interface_config import InterfaceConfig


class Sample(NamedTuple):
    name: str  # without prefix, e.g. 'bgp.peer.status'
    value: float
    tags: tuple[str, ...]  # collector-specific tags only
    kind: Literal['gauge', 'monotonic_count', 'count']


@dataclass
class ReportJob:
    report: str
    job_id: str
    carries: int = 1


@dataclass
class ReportState:
    pending: ReportJob | None = None  # polled first next run, never submitted again
    cursor: int = 0  # index in `REPORTS` of the next report to submit; back to 0 once a cycle of all of them is done


@dataclass
class FirewallState:
    # `show interface all` rows, kept when the call fails; `interface_map` is None until it first answers.
    interface_rows: list[Element] = field(default_factory=list)
    interface_map: dict[str, Element] | None = None
    # `show config running` interface settings, kept when the read fails; None until it first answers.
    interface_config: dict[str, InterfaceConfig] | None = None
    vsys: list[str] = field(default_factory=lambda: ['vsys1'])
    ha_state: str | None = None
    # Written by `vpn`, read by `interfaces`, which owns the tunnel counters: None until `vpn` first answers.
    tunnel_tags: dict[str, tuple[str, ...]] | None = None
    tunnel_states: dict[str, str] = field(default_factory=dict)
    # Keys of the warnings already logged for this firewall (see `CollectContext.warning`).
    warned: set[str] = field(default_factory=set)
    reports: ReportState = field(default_factory=ReportState)
    # Collectors that ran but stay due, as a job of theirs is still running: they run again next run.
    still_due: set[str] = field(default_factory=set)


@dataclass
class CollectContext:
    client: PanosClient
    identity: DeviceIdentity
    state: FirewallState
    config: InstanceConfig
    log: CheckLoggingAdapter
    ip: str
    # `state.tunnel_tags` as it was when the run started: what `interfaces` tags the tunnel counters with, so that
    # whether they are sent does not depend on which of the parallel collectors finishes first.
    tunnel_tags: dict[str, tuple[str, ...]] | None = None
    clock: Callable[[], float] = time.monotonic
    read_cache: Callable[[str], str] = lambda key: ''
    write_cache: Callable[[str, str], None] = lambda key, value: None

    def warning(self, msg: str, *args: object, key: str | None = None, once: bool = True) -> None:
        """Log the warning the first time `key` (by default, the formatted message) is seen for this firewall, at debug
        level after that. With `once=False`, log it at warning level every time."""
        text = msg % args if args else msg
        if not once:
            self.log.warning('%s: %s', self.ip, text)
            return
        warn_once(self.log, self.state.warned, text if key is None else key, '%s: %s', self.ip, text)

    def debug(self, msg: str, *args: object) -> None:
        self.log.debug('%s: %s', self.ip, msg % args if args else msg)


Collector = Callable[[CollectContext], list[Sample]]


def read_each[T, R](
    items: Iterable[T], read: Callable[[T], R], on_error: Callable[[T, PanosError], None]
) -> Iterator[tuple[T, R]]:
    error: PanosError | None = None
    answered = False
    for item in items:
        try:
            result = read(item)
        except (PanosAuthError, PanosUnreachable):
            raise
        except PanosError as e:
            on_error(item, e)
            error = e
            continue
        answered = True
        yield item, result
    if error is not None and not answered:
        raise error
