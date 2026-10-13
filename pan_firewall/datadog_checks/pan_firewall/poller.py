# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from datadog_checks.base.utils.http import RequestsWrapper

from .api import PanosClient, api_url
from .auth import KeyManager
from .collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState, Sample
from .errors import PanosError, PanosTimeout
from .identity import DeviceIdentity, device_ip, global_tags, parse_system_info, vsys_list
from .scheduler import FirewallSchedule

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck

    from .config_models.instance import InstanceConfig
    from .firewalls import FirewallTarget

SYSTEM_INFO_CMD = '<show><system><info/></system></show>'
INTERFACE_ALL_CMD = '<show><interface>all</interface></show>'
IDENTITY = 'identity_metadata'
# Collectors of one firewall run at once; the client's own semaphore caps the calls in flight at the same number.
COLLECTOR_WORKERS = 2

# Collectors behind an opt-in or opt-out option, to the `InstanceConfig` field that enables them.
OPTIONAL_COLLECTORS = {
    'global_counters': 'collect_global_counters',
    'ospf': 'collect_ospf',
    'reports': 'collect_reports',
    'threats': 'collect_threats',
}


@dataclass
class CollectorRun:
    """The outcome of `FirewallPoller.run_collectors()`."""

    ran: list[str] = field(default_factory=list)  # succeeded, failed or timed out
    timed_out: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # not started because a call timed out earlier in the run


class FirewallPoller:
    """Polls one firewall: identity, due collectors, `can_connect` and `api.authentication.status`.

    It owns everything kept per firewall between runs: the HTTP session, the API key, the schedule and the state.
    """

    def __init__(self, check: AgentCheck, target: FirewallTarget, config: InstanceConfig):
        self.check = check
        self.target = target
        self.config = config
        self.log = check.log
        self.ip = device_ip(target)
        # The model's default (30 s), not the wrapper's (10 s), applies when the instance sets no `timeout`.
        instance = {'timeout': config.timeout, **(check.instance or {})}
        http = RequestsWrapper(instance, check.init_config, check.HTTP_CONFIG_REMAPPER, check.log)
        http.persist_connections = True
        self.keys = KeyManager(http, api_url(target.ip, target.port), target.credentials)
        self.client = PanosClient(http, target.ip, target.port, self.keys, check.log)
        self.schedule = FirewallSchedule()
        self.state = FirewallState()
        self.identity = self._load_identity()
        if self.identity is not None:
            self.state.vsys = vsys_list(self.identity, self.state.interface_rows, config.vsys)
        self._can_connect: int | None = None
        self._auth_status: int | None = None

    @property
    def _cache_key(self) -> str:
        # Keyed by device IP: before a static firewall first answers, its IP is all the check knows.
        return f'identity:{self.ip}'

    def run(self) -> None:
        start = time.monotonic()
        # One keygen attempt per run after a rejected one (the KeyManager latches until reset).
        self.keys.reset_failure()
        due = self.schedule.due(self._enabled(), identity_missing=self.identity is None)
        ran = []
        timed_out = []
        if IDENTITY in due:
            self._refresh_identity()
            ran.append(IDENTITY)
            # Nothing else has called the firewall yet this run.
            if self.client.timed_out:
                timed_out.append(IDENTITY)
        collectors = [name for name in due if name in COLLECT_FUNCTIONS]
        skipped = []
        if timed_out:
            skipped = collectors
        # Without an identity, metrics could not carry the device tags: leave the collectors due for the next run.
        elif self.identity is not None and collectors:
            outcome = self.run_collectors(collectors, self.identity)
            ran.extend(outcome.ran)
            timed_out.extend(outcome.timed_out)
            skipped = outcome.skipped
        if timed_out:
            self.log.warning(
                'pan_firewall %s: %s timed out after %gs; skipped for this run: %s',
                self.ip,
                ', '.join(timed_out),
                self.config.timeout,
                ', '.join(skipped) or 'none',
            )
        # Skipped collectors stay due, so they run first thing next run.
        self.schedule.mark_run(ran)
        stats = self.client.take_stats()
        if stats.calls:
            self._can_connect = 1 if stats.answered else 0
            self._auth_status = 1 if self.keys.auth_failed or stats.auth_rejected else 0
        # With nothing called this run, the last result is sent again.
        tags = self.tags()
        if self._can_connect is not None:
            self.check.gauge('can_connect', self._can_connect, tags=tags)
        if self._auth_status is not None:
            self.check.gauge('api.authentication.status', self._auth_status, tags=tags)
        self.log.debug('pan_firewall %s: %d calls in %.2fs', self.ip, stats.calls, time.monotonic() - start)

    def run_collectors(self, names: Iterable[str], identity: DeviceIdentity) -> CollectorRun:
        """Run the named collectors, `COLLECTOR_WORKERS` at a time, and submit their samples.

        Once a call times out, collectors not started yet are skipped: a hung firewall costs one timeout per
        collector in flight, not one per collector. A collector must let PanosTimeout propagate. A failing
        collector is logged and does not stop the others.

        Collectors share the client's 2 in-flight slots. `iter_log_entries` holds one slot until exhausted, so a
        collector must never call `client.op()` while iterating log entries.
        """
        ctx = CollectContext(client=self.client, identity=identity, state=self.state, config=self.config, log=self.log)
        with ThreadPoolExecutor(max_workers=COLLECTOR_WORKERS, thread_name_prefix=f'pan_firewall-{self.ip}') as pool:
            futures = {name: pool.submit(self._run_collector, name, ctx) for name in names}
        outcome = CollectorRun()
        # Samples are submitted from this thread, in collector order, once every collector is done.
        for name, future in futures.items():
            try:
                samples = future.result()
            except PanosTimeout:
                outcome.timed_out.append(name)
            except PanosError as e:
                self.log.warning('pan_firewall %s: collector %s failed: %s', self.ip, name, e)
            except Exception as e:
                # A bug or an unexpected shape: the traceback is what tells them apart.
                self.log.warning('pan_firewall %s: collector %s failed: %s', self.ip, name, e, exc_info=True)
            else:
                if samples is None:
                    outcome.skipped.append(name)
                    continue
                self.submit(samples)
            outcome.ran.append(name)
        return outcome

    def _run_collector(self, name: str, ctx: CollectContext) -> list[Sample] | None:
        """Run one collector, or return None without starting it once a call has timed out this run."""
        if self.client.timed_out:
            return None
        return COLLECT_FUNCTIONS[name](ctx)

    def submit(self, samples: Iterable[Sample]) -> None:
        tags = self.tags()
        submit = {'gauge': self.check.gauge, 'monotonic_count': self.check.monotonic_count, 'count': self.check.count}
        for sample in samples:
            submit[sample.kind](sample.name, sample.value, tags=[*tags, *sample.tags])

    def tags(self) -> list[str]:
        return global_tags(self.identity, self.target, self.config.namespace or 'default', self.config.tags or ())

    def _enabled(self) -> set[str]:
        enabled = {name for name in COLLECT_FUNCTIONS if getattr(self.config, OPTIONAL_COLLECTORS.get(name, ''), True)}
        enabled.add(IDENTITY)
        return enabled

    def _refresh_identity(self) -> None:
        try:
            identity = parse_system_info(self.client.op(SYSTEM_INFO_CMD))
        except PanosTimeout:
            # `run()` reports it, with the collectors it cuts off.
            return
        except PanosError as e:
            self.log.warning('pan_firewall %s: cannot read the system info: %s', self.ip, e)
            return
        try:
            interfaces = self.client.op(INTERFACE_ALL_CMD)
        except PanosError as e:
            # The identity does not depend on it; interface tags and vsys detection keep their last value.
            self.log.debug('pan_firewall %s: cannot read the interfaces: %s', self.ip, e)
        else:
            self.state.interface_rows = interfaces.findall('./result/ifnet/entry')
            self.state.interface_map = {
                name: entry for entry in interfaces.findall('./result/hw/entry') if (name := entry.findtext('name'))
            }
        self.state.vsys = vsys_list(identity, self.state.interface_rows, self.config.vsys)
        if identity != self.identity:
            self.check.write_persistent_cache(self._cache_key, identity.to_json())
        self.identity = identity

    def _load_identity(self) -> DeviceIdentity | None:
        raw = self.check.read_persistent_cache(self._cache_key)
        if not raw:
            return None
        try:
            return DeviceIdentity.from_json(raw)
        except (ValueError, TypeError) as e:
            self.log.debug('pan_firewall %s: ignoring the cached identity: %s', self.ip, e)
            return None
