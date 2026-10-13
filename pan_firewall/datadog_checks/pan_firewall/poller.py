# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import json
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING

from datadog_checks.base.utils.http import RequestsWrapper

from .api import PanosClient, api_url
from .auth import KeyManager
from .collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState, Sample
from .errors import PanosError
from .identity import DeviceIdentity, device_ip, global_tags, parse_system_info, vsys_list
from .scheduler import FirewallSchedule

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck

    from .config_models.instance import InstanceConfig
    from .firewalls import FirewallTarget

SYSTEM_INFO_CMD = '<show><system><info/></system></show>'
INTERFACE_ALL_CMD = '<show><interface>all</interface></show>'
IDENTITY = 'identity_metadata'

# Collectors behind an opt-in or opt-out option, to the `InstanceConfig` field that enables them.
OPTIONAL_COLLECTORS = {
    'global_counters': 'collect_global_counters',
    'ospf': 'collect_ospf',
    'reports': 'collect_reports',
    'threats': 'collect_threats',
}


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
        http = RequestsWrapper(check.instance or {}, check.init_config, check.HTTP_CONFIG_REMAPPER, check.log)
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
        if IDENTITY in due:
            self._refresh_identity()
            ran.append(IDENTITY)
        collectors = [name for name in due if name in COLLECT_FUNCTIONS]
        # Without an identity, metrics could not carry the device tags: leave the collectors due for the next run.
        if self.identity is not None and collectors:
            self.run_collectors(collectors, self.identity)
            ran.extend(collectors)
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

    def run_collectors(self, names: Iterable[str], identity: DeviceIdentity) -> None:
        """Run the named collectors and submit their samples.

        Collectors share the client's 2 in-flight slots. `iter_log_entries` holds one slot until exhausted, so a
        collector must never call `client.op()` while iterating log entries.
        """
        ctx = CollectContext(client=self.client, identity=identity, state=self.state, config=self.config, log=self.log)
        for name in names:
            try:
                samples = COLLECT_FUNCTIONS[name](ctx)
            except PanosError as e:
                self.log.warning('pan_firewall %s: collector %s failed: %s', self.ip, name, e)
                continue
            self.submit(samples)

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
            self.check.write_persistent_cache(self._cache_key, json.dumps(dataclasses.asdict(identity)))
        self.identity = identity

    def _load_identity(self) -> DeviceIdentity | None:
        raw = self.check.read_persistent_cache(self._cache_key)
        if not raw:
            return None
        try:
            return DeviceIdentity(**json.loads(raw))
        except (ValueError, TypeError) as e:
            self.log.debug('pan_firewall %s: ignoring the cached identity: %s', self.ip, e)
            return None
