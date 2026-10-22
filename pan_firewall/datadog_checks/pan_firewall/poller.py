# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from .api import PanosClient
from .auth import KeyManager
from .collectors import COLLECTORS
from .collectors.base import CollectContext, FirewallState, Sample
from .collectors.interfaces import parse_interface_all, parse_interface_speeds
from .collectors.jobs import busy_jobs
from .constants import IDENTITY
from .errors import PanosError, PanosSkipped, PanosUnreachable
from .identity import DeviceIdentity, configured_vsys, global_tags, parse_system_info, vsys_list
from .interface_config import INTERFACE_CONFIG_CMD, parse_interface_config
from .metadata import build_device, build_interfaces
from .ndm_models import DeviceMetadata, InterfaceMetadata, batch_payloads
from .scheduler import BusyGate, FirewallSchedule, Result

if TYPE_CHECKING:
    from .check import PanFirewallCheck
    from .firewalls import FirewallTarget

SYSTEM_INFO_CMD = '<show><system><info/></system></show>'
INTERFACE_ALL_CMD = '<show><interface>all</interface></show>'
# Name of the commit check in the unreachable warning.
JOBS_CHECK = 'jobs'
# Collectors of one firewall run at once, and calls the client lets in flight.
COLLECTOR_WORKERS = 2

OPTIONAL_COLLECTORS = {
    'global_counters': 'collect_global_counters',
    'ospf': 'collect_ospf',
    'reports': 'collect_reports',
    'threats': 'collect_threats',
}


class FirewallPoller:
    """Polls one firewall, and keeps what lasts between its runs: client, schedule, identity and state."""

    def __init__(self, check: PanFirewallCheck, target: FirewallTarget):
        self.check = check
        self.target = target
        self.config = check.config
        self.log = check.log
        self._cache_key = f'identity:{target.ip}'
        keys = KeyManager(check.http, target.ip, target.credentials)
        self.client = PanosClient(check.http, target.ip, keys, check.log, max_in_flight=COLLECTOR_WORKERS)
        self.schedule = FirewallSchedule()
        self._busy_gate = BusyGate(check.log, target.ip)
        self.state = FirewallState(vsys=configured_vsys(self.config.vsys) or ['vsys1'])
        self.identity = self._load_identity()
        self._can_connect: int | None = None
        self._auth_status: int | None = None
        # The `can_connect` the last metadata was sent with: a different one sends the metadata again at once.
        self._metadata_status: int | None = None

    @property
    def ip(self) -> str:
        return self.target.ip

    def run(self) -> None:
        start = time.monotonic()
        self.client.start_run()
        try:
            self._run()
        finally:
            self.log.debug('%s: %d calls in %.2fs', self.ip, self.client.stats.calls, time.monotonic() - start)

    def _run(self) -> None:
        due = self.schedule.due(self._enabled(), identity_missing=self.identity is None)
        results = self._collect(due)
        self._warn_if_unreachable(results)
        self.schedule.record(results)
        if results.get(IDENTITY) is Result.RAN and self.state.interface_map is None:
            # The identity was read but not the interfaces: try again soon rather than in 30 minutes, as the interface
            # tags and the NDM interfaces depend on it.
            self.schedule.mark_failed([IDENTITY])
        if self.client.stats.key_regenerated:
            # A rejected key that had worked may mean another unit answers here: read the identity again next run.
            self.schedule.make_due(IDENTITY)
        self._send_health()
        self._send_metadata(identity_read=results.get(IDENTITY) is Result.RAN)

    def _warn_if_unreachable(self, results: dict[str, Result]) -> None:
        """One warning per run that lost the firewall, naming the calls that could not reach it and what was skipped.

        It reads the client rather than `results`: a collector that caught the error itself still lost the firewall.
        """
        if (reason := self.client.stats.unreachable) is None:
            return
        self.log.warning(
            '%s: could not reach the firewall (%s) during %s; skipped for this run: %s',
            self.ip,
            reason,
            ', '.join(names_with(results, Result.UNREACHABLE)) or 'a call',
            ', '.join(names_with(results, Result.SKIPPED)) or 'none',
        )

    def _send_health(self) -> None:
        stats = self.client.stats
        if stats.calls:
            self._can_connect = 1 if stats.answered else 0
            # Only a run where the firewall answered says whether the credentials work; until one does, nothing is sent.
            if stats.auth_rejected:
                self._auth_status = 1
            elif stats.answered:
                self._auth_status = 0
        tags = self._tags()
        if self._can_connect is not None:
            self.check.gauge('can_connect', self._can_connect, tags=tags)
        if self._auth_status is not None:
            self.check.gauge('api.authentication.status', self._auth_status, tags=tags)

    def _send_metadata(self, identity_read: bool) -> None:
        """Send the device and its interfaces after each identity read that succeeds (30 min), and when `can_connect`
        flips. A failed read sends nothing rather than the last identity again."""
        identity = self.identity
        if not self.config.send_ndm_metadata or identity is None or identity.serial is None:
            return
        if self._can_connect is None or (self._can_connect == self._metadata_status and not identity_read):
            return
        self._metadata_status = self._can_connect
        namespace = self.config.namespace or 'default'
        device = build_device(identity, self.ip, namespace, self._tags(), self._can_connect, self.state.ha_state)
        records: list[DeviceMetadata | InterfaceMetadata] = [device, *build_interfaces(identity.serial, self.state)]
        for payload in batch_payloads(namespace, records):
            self.check.event_platform_event(
                json.dumps(payload.model_dump(exclude_none=True)), 'network-devices-metadata'
            )

    def _busy(self) -> bool:
        """Run the jobs check; True skips this run's collectors (a commit or update is in progress).

        A failed jobs check is warned about every time and never blocks collection. Raises PanosUnreachable when it
        cannot reach the firewall.
        """
        try:
            jobs = busy_jobs(self.client)
        except PanosUnreachable:
            self._busy_gate.end()
            raise
        except PanosError as e:
            self.log.warning(
                '%s: cannot check for a commit or content update in progress, collecting anyway: %s', self.ip, e
            )
            jobs = []
        return self._busy_gate.skip(jobs, self.schedule.now())

    def _collect(self, due: list[str]) -> dict[str, Result]:
        """Run the jobs check, then the due identity and collectors."""
        if not due:
            return {}
        try:
            if self._busy():
                return {}
        except PanosUnreachable:
            return {JOBS_CHECK: Result.UNREACHABLE} | dict.fromkeys(due, Result.SKIPPED)

        results = {}
        if IDENTITY in due:
            results[IDENTITY] = self._run_identity()
        collectors = [name for name in due if name in COLLECTORS]
        if not collectors:
            return results

        if self.client.stats.unreachable is not None:
            results |= dict.fromkeys(collectors, Result.SKIPPED)
        # Without an identity, metrics could not carry the device tags: leave the collectors due for the next run.
        elif self.identity is not None:
            results |= self._run_collectors(collectors, self.identity)
        return results

    def _run_identity(self) -> Result:
        """Read the identity and the interfaces."""
        try:
            identity = self._read_system_info()
        except PanosUnreachable:
            return Result.UNREACHABLE
        if identity is None:
            return Result.FAILED
        self._set_identity(identity)
        self._read_interfaces(identity)
        return Result.RAN

    def _run_collectors(self, names: Iterable[str], identity: DeviceIdentity) -> dict[str, Result]:
        """Run the named collectors, `COLLECTOR_WORKERS` at a time, and submit their samples.

        Once a call cannot reach the firewall, the rest are skipped and stay due. A failing collector is logged and
        does not stop the others. A collector whose job is still running gets no result, so it stays due.
        `read_log_job` holds one of the `COLLECTOR_WORKERS` slots while it calls back: never call the client from it.
        """
        ctx = CollectContext(
            client=self.client,
            identity=identity,
            state=self.state,
            config=self.config,
            log=self.log,
            ip=self.ip,
            # `interfaces` uses the tags `vpn` stored on an earlier run: the first run sends no tunnel counters, and a
            # new or renamed tunnel gets its tags one run late. Deliberate: a tunnel series without its tags would be a
            # useless monotonic_count context, and making `interfaces` wait for `vpn` would couple the two collectors'
            # schedules.
            tunnel_tags=self.state.tunnel_tags,
            clock=self.schedule.now,
            read_cache=self.check.read_persistent_cache,
            write_cache=self.check.write_persistent_cache,
        )
        self.state.still_due.clear()
        with ThreadPoolExecutor(max_workers=COLLECTOR_WORKERS, thread_name_prefix=f'pan_firewall-{self.ip}') as pool:
            futures = {name: pool.submit(self._run_collector, name, ctx) for name in names}
        results = {}
        for name, future in futures.items():
            try:
                self._submit(future.result())
            except PanosSkipped:
                results[name] = Result.SKIPPED
            except PanosUnreachable:
                results[name] = Result.UNREACHABLE
            except PanosError as e:
                self.log.warning('%s: collector %s failed: %s', self.ip, name, e)
                results[name] = Result.FAILED
            except Exception as e:
                # A bug or an unexpected shape: the traceback is what tells them apart.
                self.log.warning('%s: collector %s failed: %s', self.ip, name, e, exc_info=True)
                results[name] = Result.FAILED
            else:
                if name not in self.state.still_due:
                    results[name] = Result.RAN
        return results

    def _run_collector(self, name: str, ctx: CollectContext) -> list[Sample]:
        if self.client.stats.unreachable is not None:
            raise PanosSkipped(f'not running {name}: an earlier call could not reach {self.ip}')
        return COLLECTORS[name](ctx)

    def _submit(self, samples: Iterable[Sample]) -> None:
        tags = self._tags()
        for sample in samples:
            getattr(self.check, sample.kind)(sample.name, sample.value, tags=[*tags, *sample.tags])

    def _tags(self) -> list[str]:
        return global_tags(self.identity, self.target, self.config.namespace or 'default', self.config.tags or ())

    def _enabled(self) -> set[str]:
        return {
            name
            for name in COLLECTORS
            if name not in OPTIONAL_COLLECTORS or getattr(self.config, OPTIONAL_COLLECTORS[name])
        } | {IDENTITY}

    def _read_system_info(self) -> DeviceIdentity | None:
        """The identity from `show system info`, or None when it could not be read. PanosUnreachable propagates."""
        try:
            return parse_system_info(self.client.op(SYSTEM_INFO_CMD))
        except PanosUnreachable:
            raise
        except PanosError as e:
            self.log.warning('%s: cannot read the system info: %s', self.ip, e)
            return None

    def _set_identity(self, identity: DeviceIdentity) -> None:
        """Replace the known identity with one just read, and cache it."""
        old = self.identity
        if old is not None and old.serial and identity.serial != old.serial:
            self.log.info('%s: the serial changed from %s to %s', self.ip, old.serial, identity.serial)
            self.state = FirewallState()
        # The cache gives the next agent start the device tags before its first read.
        if identity != old:
            self.check.write_persistent_cache(self._cache_key, identity.to_json())
        self.identity = identity

    def _read_interfaces(self, identity: DeviceIdentity) -> None:
        """Read `show interface all` into the state, send `interface.speed`, detect the vsys, and read the interface
        config for the metadata.

        When the read fails, interface tags and vsys detection keep the last rows read.
        """
        try:
            interfaces = self.client.op(INTERFACE_ALL_CMD)
        except PanosUnreachable:
            pass  # `_warn_if_unreachable` reports it.
        except PanosError as e:
            self._warn_once(
                'interface_all',
                'cannot read the interfaces, so metrics have no interface tags and NDM gets no interfaces: %s',
                e,
            )
        else:
            self.state.interface_rows, self.state.interface_map = parse_interface_all(interfaces)
            # `interface.speed` follows the identity's 30-minute schedule, as it comes from the interfaces read here.
            self._submit(parse_interface_speeds(self.state, identity.serial, self._debug))
        self.state.vsys = vsys_list(identity, self.state.interface_rows, self.config.vsys)
        self._read_interface_config()

    def _read_interface_config(self) -> None:
        """Read the interface comments and link states for the metadata. When the read fails, keep the last ones."""
        if not self.config.send_ndm_metadata or self.client.stats.unreachable is not None:
            return
        try:
            # A refusal is the role lacking a permission, not a rejected key: it must not renew the key.
            root = self.client.op(INTERFACE_CONFIG_CMD, renew_on_auth_error=False)
        except PanosError as e:
            self._warn_once(
                'interface_config',
                'cannot read the interface config, so interfaces have no admin status or description. To send them, '
                'allow `show config running` in the XML API Operational Requests of the Agent role: %s',
                e,
            )
        else:
            self.state.interface_config = parse_interface_config(root)

    def _warn_once(self, key: str, msg: str, *args: object) -> None:
        """Log the warning the first time `key` is seen for this firewall, at debug level after that: a failure that
        lasts, such as a role without a permission, would otherwise repeat it every 30 minutes."""
        log = self.log.debug if key in self.state.warned else self.log.warning
        self.state.warned.add(key)
        log('%s: ' + msg, self.ip, *args)

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


def names_with(results: dict[str, Result], *wanted: Result) -> list[str]:
    return [name for name, result in results.items() if result in wanted]
