# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .api import PanosClient
from .auth import KeyManager
from .collectors import (  # noqa: F401  (importing the modules registers their collectors)
    COLLECT_FUNCTIONS,
    CollectContext,
    FirewallState,
    Sample,
    counters,
    dataplane,
    ha,
    interfaces,
    licenses,
    reports,
    routing,
    rules,
    system,
    threats,
    vpn,
)
from .collectors.interfaces import parse_interface_speeds
from .collectors.jobs import busy_jobs
from .constants import COMMIT_SKIP_MAX_SECONDS, IDENTITY
from .errors import PanosError, PanosSkipped, PanosUnreachable
from .identity import DeviceIdentity, global_tags, parse_system_info, vsys_list
from .metadata import build_device, build_interfaces
from .ndm_models import DeviceMetadata, InterfaceMetadata, batch_payloads
from .scheduler import FirewallSchedule

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck

    from .config_models.instance import InstanceConfig
    from .firewalls import FirewallTarget

SYSTEM_INFO_CMD = '<show><system><info/></system></show>'
INTERFACE_ALL_CMD = '<show><interface>all</interface></show>'
# Name of the commit check in the unreachable warning.
JOBS_CHECK = 'jobs'
# Collectors of one firewall run at once; the client's own semaphore caps the calls in flight at the same number.
COLLECTOR_WORKERS = 2

OPTIONAL_COLLECTORS = {
    'global_counters': 'collect_global_counters',
    'ospf': 'collect_ospf',
    'reports': 'collect_reports',
    'threats': 'collect_threats',
}


@dataclass
class CollectorRun:
    ran: list[str] = field(default_factory=list)  # succeeded, failed, or could not reach the firewall
    unreachable: list[str] = field(default_factory=list)
    # Not run, or cut short, because an earlier call of the run could not reach the firewall.
    skipped: list[str] = field(default_factory=list)


class FirewallPoller:
    """Polls one firewall, and keeps what lasts between its runs: API key, schedule and state."""

    def __init__(self, check: AgentCheck, target: FirewallTarget, config: InstanceConfig):
        self.check = check
        self.target = target
        self.config = config
        self.log = check.log
        self.ip = target.ip
        # Keyed by device IP: before a static firewall first answers, its IP is all the check knows.
        self._cache_key = f'identity:{self.ip}'
        self.keys = KeyManager(check.http, target.ip, target.credentials)
        self.client = PanosClient(check.http, target.ip, self.keys, check.log)
        self.schedule = FirewallSchedule()
        self.state = FirewallState()
        self.identity = self._load_identity()
        if self.identity is not None:
            self.state.vsys = vsys_list(self.identity, self.state.interface_rows, config.vsys)
        self._can_connect: int | None = None
        self._auth_status: int | None = None
        # The `can_connect` the last metadata was sent with: a different one sends the metadata again at once.
        self._metadata_status: int | None = None
        # Schedule-clock start of the current busy period, None while the firewall is not busy.
        self._busy_since: float | None = None
        self._busy_cap_warned = False
        self._jobs_error_warned = False

    def run(self) -> None:
        start = time.monotonic()
        # Clears what a run that raised may have left, such as the failure that makes every call fail fast.
        self.client.start_run()
        try:
            self._run()
        finally:
            self.log.debug('%s: %d calls in %.2fs', self.ip, self.client.stats.calls, time.monotonic() - start)

    def _run(self) -> None:
        # One keygen attempt per run after a rejected one (the KeyManager latches until then).
        self.keys.allow_one_keygen()
        due = self.schedule.due(self._enabled(), identity_missing=self.identity is None)
        outcome = CollectorRun()
        if due:
            busy = self._busy()
            # The jobs check is the run's first call: if it fails to reach the firewall, the whole run is cut off.
            if self.client.unreachable is not None:
                outcome = CollectorRun(unreachable=[JOBS_CHECK], skipped=due)
            elif not busy:
                outcome = self._collect(due)
        # Also when a collector caught the exception itself, so no name was recorded.
        if (reason := self.client.unreachable) is not None:
            self.log.warning(
                '%s: could not reach the firewall (%s) during %s; skipped for this run: %s',
                self.ip,
                reason,
                ', '.join(outcome.unreachable) or 'a call',
                ', '.join(outcome.skipped) or 'none',
            )
        # Skipped collectors, and every collector of a busy run, stay due, so they run first thing next run.
        self.schedule.mark_run(outcome.ran)
        stats = self.client.stats
        if stats.key_regenerated:
            # A rejected key that had worked may mean another unit answers here: read the identity again next run.
            self.schedule.make_due(IDENTITY)
        if stats.calls:
            self._can_connect = 1 if stats.answered else 0
            # A run with no verdict on the credentials (nothing answered) keeps the last one; the first reports 0.
            if stats.auth_rejected:
                self._auth_status = 1
            elif stats.answered or self._auth_status is None:
                self._auth_status = 0
        # With nothing called this run, the last result is sent again.
        tags = self.tags()
        if self._can_connect is not None:
            self.check.gauge('can_connect', self._can_connect, tags=tags)
        if self._auth_status is not None:
            self.check.gauge('api.authentication.status', self._auth_status, tags=tags)
        self._send_metadata(outcome)

    def _send_metadata(self, outcome: CollectorRun) -> None:
        """Send the device and its interfaces on the identity's schedule (30 min), and when `can_connect` flips."""
        identity = self.identity
        if not self.config.send_ndm_metadata or identity is None or identity.serial is None:
            return
        if self._can_connect is None or (self._can_connect == self._metadata_status and IDENTITY not in outcome.ran):
            return
        self._metadata_status = self._can_connect
        namespace = self.config.namespace or 'default'
        device = build_device(identity, self.ip, namespace, self.tags(), self._can_connect, self.state.ha_state)
        records: list[DeviceMetadata | InterfaceMetadata] = [device, *build_interfaces(identity.serial, self.state)]
        for payload in batch_payloads(namespace, records):
            self.check.event_platform_event(
                json.dumps(payload.model_dump(exclude_none=True)), 'network-devices-metadata'
            )

    def _busy(self) -> bool:
        """Run the jobs check; True skips this run's collectors (a commit or update is in progress).

        Skipping lasts at most COMMIT_SKIP_MAX_SECONDS per busy period, then the firewall is collected with one
        warning. A failed jobs check never blocks collection, and is warned about once per episode.
        """
        try:
            jobs = busy_jobs(self.client)
        except PanosUnreachable:
            self._busy_since = None
            return False
        except PanosError as e:
            self._busy_since = None
            if not self._jobs_error_warned:
                self._jobs_error_warned = True
                self.log.warning(
                    '%s: cannot check for a commit or content update in progress, collecting anyway: %s',
                    self.ip,
                    e,
                )
            return False
        self._jobs_error_warned = False
        if not jobs:
            self._busy_since = None
            return False
        job = jobs[0]
        now = self.schedule.now()
        if self._busy_since is None:
            self._busy_since = now
            self._busy_cap_warned = False
        if now - self._busy_since < COMMIT_SKIP_MAX_SECONDS:
            self.log.debug('%s: %s job %s in progress, skipping collection this run', self.ip, job.type, job.id)
            return True
        if not self._busy_cap_warned:
            self._busy_cap_warned = True
            self.log.warning(
                '%s: %s job %s still in progress after %ds of skipping; collecting anyway',
                self.ip,
                job.type,
                job.id,
                COMMIT_SKIP_MAX_SECONDS,
            )
        return False

    def _collect(self, due: list[str]) -> CollectorRun:
        outcome = CollectorRun()
        if IDENTITY in due:
            self._refresh_identity()
            outcome.ran.append(IDENTITY)
            # The jobs check answered, so a failure to reach the firewall now is the identity's.
            if self.client.unreachable is not None:
                outcome.unreachable.append(IDENTITY)
        collectors = [name for name in due if name in COLLECT_FUNCTIONS]
        if outcome.unreachable:
            outcome.skipped = collectors
        # Without an identity, metrics could not carry the device tags: leave the collectors due for the next run.
        elif self.identity is not None and collectors:
            collected = self.run_collectors(collectors, self.identity)
            outcome.ran.extend(collected.ran)
            outcome.unreachable.extend(collected.unreachable)
            outcome.skipped = collected.skipped
        return outcome

    def run_collectors(self, names: Iterable[str], identity: DeviceIdentity) -> CollectorRun:
        """Run the named collectors, `COLLECTOR_WORKERS` at a time, and submit their samples.

        Once a call cannot reach the firewall, the rest are skipped and stay due. A failing collector is logged and
        does not stop the others. `open_log_job` holds one of the 2 slots: never call `client.op()` inside it.
        """
        ctx = CollectContext(
            client=self.client,
            identity=identity,
            state=self.state,
            config=self.config,
            log=self.log,
            ip=self.ip,
            tunnel_tags=self.state.tunnel_tags,
            clock=self.schedule.now,
            read_cache=self.check.read_persistent_cache,
            write_cache=self.check.write_persistent_cache,
        )
        self.state.still_due.clear()
        with ThreadPoolExecutor(max_workers=COLLECTOR_WORKERS, thread_name_prefix=f'pan_firewall-{self.ip}') as pool:
            futures = {name: pool.submit(self._run_collector, name, ctx) for name in names}
        outcome = CollectorRun()
        # Samples are submitted from this thread, in collector order, once every collector is done.
        for name, future in futures.items():
            try:
                samples = future.result()
                if samples is None:
                    outcome.skipped.append(name)
                    continue
                self.submit(samples)
                if name in self.state.still_due:
                    continue
            except PanosSkipped:
                outcome.skipped.append(name)
                continue
            except PanosUnreachable:
                outcome.unreachable.append(name)
            except PanosError as e:
                self.log.warning('%s: collector %s failed: %s', self.ip, name, e)
            except Exception as e:
                # A bug or an unexpected shape: the traceback is what tells them apart.
                self.log.warning('%s: collector %s failed: %s', self.ip, name, e, exc_info=True)
            outcome.ran.append(name)
        return outcome

    def _run_collector(self, name: str, ctx: CollectContext) -> list[Sample] | None:
        if self.client.unreachable is not None:
            return None
        return COLLECT_FUNCTIONS[name](ctx)

    def submit(self, samples: Iterable[Sample]) -> None:
        tags = self.tags()
        for sample in samples:
            getattr(self.check, sample.kind)(sample.name, sample.value, tags=[*tags, *sample.tags])

    def tags(self) -> list[str]:
        return global_tags(self.identity, self.target, self.config.namespace or 'default', self.config.tags or ())

    def _enabled(self) -> set[str]:
        enabled = {name for name in COLLECT_FUNCTIONS if getattr(self.config, OPTIONAL_COLLECTORS.get(name, ''), True)}
        enabled.add(IDENTITY)
        return enabled

    def _refresh_identity(self) -> None:
        try:
            identity = parse_system_info(self.client.op(SYSTEM_INFO_CMD))
        except PanosUnreachable:
            # `run()` reports it, with the collectors it cuts off.
            return
        except PanosError as e:
            self.log.warning('%s: cannot read the system info: %s', self.ip, e)
            return
        previous = self.identity.serial if self.identity else None
        if previous and identity.serial != previous:
            # Another unit answers at this IP (a replaced static firewall). What was kept about the old one (pending
            # jobs, threat watermark, warnings, interface rows) does not apply to it; the collectors reload theirs.
            self.log.info('%s: the serial changed from %s to %s', self.ip, previous, identity.serial)
            self.state = FirewallState()
        try:
            interfaces = self.client.op(INTERFACE_ALL_CMD)
        except PanosError as e:
            # The identity does not depend on it; interface tags and vsys detection keep their last value.
            self.log.debug('%s: cannot read the interfaces: %s', self.ip, e)
            fresh = False
        else:
            self.state.interface_rows = interfaces.findall('./result/ifnet/entry')
            self.state.interface_map = {
                name: entry for entry in interfaces.findall('./result/hw/entry') if (name := entry.findtext('name'))
            }
            fresh = True
        self.state.vsys = vsys_list(identity, self.state.interface_rows, self.config.vsys)
        if identity != self.identity:
            self.check.write_persistent_cache(self._cache_key, identity.to_json())
        self.identity = identity
        # `interface.speed` follows this step's 30-minute schedule, as it comes from the interfaces read here.
        if fresh:
            self.submit(parse_interface_speeds(self.state, identity.serial, self._debug))

    def _debug(self, msg: str, *args: object) -> None:
        """The `debug` callable of the `parse_*` functions the poller calls itself, outside a `CollectContext`."""
        self.log.debug('%s: %s', self.ip, msg % args if args else msg)

    def _load_identity(self) -> DeviceIdentity | None:
        raw = self.check.read_persistent_cache(self._cache_key)
        if not raw:
            return None
        try:
            identity = DeviceIdentity.from_json(raw)
        except (ValueError, TypeError) as e:
            self.log.debug('%s: ignoring the cached identity: %s', self.ip, e)
            return None
        # The cache is keyed by IP: a different firewall now at this IP (a replaced unit) must not inherit it.
        if self.target.serial and identity.serial != self.target.serial:
            self.log.debug('%s: ignoring the cached identity of another firewall', self.ip)
            return None
        return identity
