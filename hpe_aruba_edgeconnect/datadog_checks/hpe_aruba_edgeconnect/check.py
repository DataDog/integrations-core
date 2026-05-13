# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import RequestsWrapper

from .client import ApplianceClient, OrchestratorClient
from .config_models import ConfigMixin
from .constants import MINUTE_STATS_INTERVAL, NDM_INTERFACE_RESOURCE_TAG
from .metrics_store import MetricsStore
from .minute_stats import MinuteStats, TunnelV2Stats
from .models import Appliance, Appliances
from .ndm_models import (
    DeviceMetadata,
    InterfaceMetadata,
    TunnelMetadata,
    batch_payloads,
    create_device_metadata,
    create_interface_metadata,
    create_tunnel_metadata,
)

_CPU_STATE_FIELDS = {
    'user': 'pUser',
    'system': 'pSys',
    'irq': 'pIRQ',
    'nice': 'pNice',
}


class HpeArubaEdgeconnectCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'hpe_aruba_edgeconnect'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.http.persist_connections = True
        # Auth is handled via session cookies from the login endpoint, not HTTP Basic Auth
        self.http.options['auth'] = None
        self._peer_lookup: dict[str, tuple[str, str]] = {}
        self._overlay_map: dict[str, str] = {}
        self._traffic_class_map: dict[str, str] = {}
        self._appliance_clients: dict[str, ApplianceClient] = {}
        self._orch_client: OrchestratorClient | None = None
        self._appliance_clients_lock = threading.Lock()

    def _get_orch_client(self) -> OrchestratorClient:
        if self._orch_client is not None:
            return self._orch_client
        client = OrchestratorClient(self.http, self.config.orch_ip)
        client.login(self.config.username, self.config.password)
        self._orch_client = client
        return client

    def check(self, _: Any) -> None:
        orch_tags = [f'orch_ip:{self.config.orch_ip}']
        try:
            orch_client = self._get_orch_client()
        except Exception:
            self.gauge('orchestrator.reachability', 0, tags=orch_tags)
            self._orch_client = None
            raise
        self.gauge('orchestrator.reachability', 1, tags=orch_tags)
        appliances = self._collect_appliances_from_orch(orch_client)
        current_ips = {ap.ip for ap in appliances}
        stale_ips = set(self._appliance_clients) - current_ips
        for ip in stale_ips:
            del self._appliance_clients[ip]
        with ThreadPoolExecutor(max_workers=self.config.max_concurrency) as pool:
            futs = {
                pool.submit(
                    self._collect_appliance,
                    ap,
                    self._peer_lookup,
                    self._overlay_map,
                    self._traffic_class_map,
                ): ap
                for ap in appliances
            }
            for f in as_completed(futs):
                ap = futs[f]
                try:
                    f.result()
                except Exception:
                    self._appliance_clients.pop(ap.ip, None)
                    self.log.warning("Failed to collect from appliance %s", ap.ip, exc_info=True)

    def _submit_metadata(
        self,
        items: list[DeviceMetadata | InterfaceMetadata | TunnelMetadata],
        collect_timestamp: int | None = None,
    ) -> None:
        if not items:
            return
        for batch in batch_payloads(self.config.namespace, items, collect_timestamp):
            self.event_platform_event(
                json.dumps(batch.model_dump(exclude_none=True)),
                "network-devices-metadata",
            )

    def _collect_appliances_from_orch(self, client: OrchestratorClient) -> Appliances:
        raw_appliances = client.get_appliances()
        if not raw_appliances:
            self.log.warning("No appliances returned from orchestrator %s", self.config.orch_ip)
            return Appliances([])
        self.log.debug("Found %d appliances from orchestrator before filtering", len(raw_appliances))
        all_appliances = [Appliance(a) for a in raw_appliances]
        self._peer_lookup = {ap.host_name: (ap.ip, ap.site or 'unknown') for ap in all_appliances if ap.host_name}
        appliances = Appliances(all_appliances)
        appliance_ips = self.config.appliance_ips.model_dump() if self.config.appliance_ips else None
        appliances.filter(appliance_ips)
        self.log.debug("Monitoring %d appliances after filtering", len(appliances))
        appliance_credentials = (
            [c.model_dump() for c in self.config.appliance_credentials] if self.config.appliance_credentials else None
        )
        appliances.resolve_credentials(
            self.config.username,
            self.config.password,
            appliance_credentials,
        )
        namespace = self.config.namespace
        devices = []
        for ap in appliances:
            tags = ap.tags(namespace)
            self.gauge('device.reachability', 1 if ap.is_reachable else 0, tags=tags)
            devices.append(create_device_metadata(ap, namespace))
        self._submit_metadata(devices)
        try:
            self._overlay_map, self._traffic_class_map = client.get_overlay_config()
        except Exception:
            self.log.warning(
                "Failed to fetch overlay config, overlay and traffic class names will use raw IDs", exc_info=True
            )
            self._overlay_map = {}
            self._traffic_class_map = {}
        return appliances

    def _create_appliance_client(self, app_ip: str, username: str, password: str) -> ApplianceClient:
        with self._appliance_clients_lock:
            cached = self._appliance_clients.get(app_ip)
            if cached is not None:
                return cached
            http = RequestsWrapper(self.instance or {}, self.init_config, self.HTTP_CONFIG_REMAPPER, self.log)
            http.persist_connections = True
            http.options['auth'] = None
            client = ApplianceClient(http, app_ip, self.log)
            client.login(username, password)
            self._appliance_clients[app_ip] = client
            return client

    def _timestamps_to_fetch(self, app_ip: str, newest: int) -> list[int]:
        raw = self.read_persistent_cache(f'last_timestamp:{app_ip}')
        last_ts = int(raw) if raw else None

        if last_ts is not None and newest == last_ts:
            return []

        max_backfill = self.config.max_backfill_minutes
        if last_ts is None:
            self.log.debug("First run for %s, collecting only the newest timestamp %d", app_ip, newest)
            return [newest]

        timestamps = []
        ts = newest
        while ts > last_ts and len(timestamps) < max_backfill:
            timestamps.append(ts)
            ts -= MINUTE_STATS_INTERVAL

        if ts > last_ts:
            self.log.warning(
                "Appliance %s is %d minutes behind; capping backfill at %d minute(s). Older data will be skipped.",
                app_ip,
                (newest - last_ts) // MINUTE_STATS_INTERVAL,
                max_backfill,
            )
        else:
            self.log.debug(
                "Catching up %d missed minute-stats archives for %s (last cached: %d, newest: %d)",
                len(timestamps),
                app_ip,
                last_ts,
                newest,
            )
        return timestamps

    def _collect_appliance(
        self,
        appliance: Appliance,
        peer_lookup: dict[str, tuple[str, str]],
        overlay_map: dict[str, str],
        traffic_class_map: dict[str, str],
    ) -> None:
        app_ip = appliance.ip
        self.log.debug("Starting collection for appliance %s", app_ip)
        client = self._create_appliance_client(app_ip, appliance.username, appliance.password)

        namespace = self.config.namespace
        base_tags = appliance.tags(namespace)
        device_id = appliance.device_id(namespace)
        newest = client.get_newest_timestamp()

        timestamps = self._timestamps_to_fetch(app_ip, newest)
        latest_tunnel_stats: list[TunnelV2Stats] = []
        if timestamps:
            store = MetricsStore()
            last_successful_ts: int | None = None
            for ts in reversed(timestamps):
                try:
                    content = client.get_minute_stats(f'st2-{ts}.tgz')
                    minute_stats = MinuteStats(content, app_ip, ts, self.log)
                    minute_stats.record(store, base_tags, device_id, traffic_class_map, overlay_map)
                except Exception:
                    self.log.warning(
                        "Failed to process minute-stats archive st2-%d.tgz for appliance %s, skipping",
                        ts,
                        app_ip,
                        exc_info=True,
                    )
                    break
                last_successful_ts = ts
                if minute_stats.tunnels:
                    latest_tunnel_stats = minute_stats.tunnels
            store.flush(self)
            if last_successful_ts is not None:
                self.write_persistent_cache(f'last_timestamp:{app_ip}', str(last_successful_ts))
        else:
            self.log.debug("Appliance %s stats are up to date (last timestamp: %d)", app_ip, newest)

        collectors: list[tuple[str, Callable[[], None]]] = [
            ('network_interfaces', lambda: self._collect_network_interfaces(client, base_tags, device_id, newest)),
            ('cpu_stats', lambda: self._collect_cpu_stats(client, base_tags, newest)),
            ('memory_stats', lambda: self._collect_memory_stats(client, base_tags)),
            ('disk_stats', lambda: self._collect_disk_stats(client, base_tags)),
            ('alarm_stats', lambda: self._collect_alarm_stats(client, base_tags)),
            ('system_info', lambda: self._collect_system_info(client, base_tags)),
        ]
        if latest_tunnel_stats:
            collectors.append(
                (
                    'tunnel_metadata',
                    lambda: self._submit_metadata(
                        [
                            create_tunnel_metadata(
                                t,
                                app_ip,
                                appliance.site,
                                namespace,
                                peer_lookup,
                                overlay_map,
                                self.log,
                            )
                            for t in latest_tunnel_stats
                        ],
                        newest,
                    ),
                )
            )
        max_workers = min(len(collectors), self.config.max_concurrency)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = {pool.submit(fn): name for name, fn in collectors}
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception:
                    self.log.warning("Collection step %s failed for appliance %s", futs[f], app_ip, exc_info=True)

    def _collect_network_interfaces(
        self,
        client: ApplianceClient,
        base_tags: list[str],
        device_id: str,
        collect_timestamp: int,
    ) -> None:
        data = client.get_network_interfaces()
        namespace = self.config.namespace
        interfaces = []
        for iface in data.get('ifInfo', []):
            ifname = iface.get('ifname', 'unknown')
            iface_tags = base_tags + [
                f'interface_name:{ifname}',
                f'{NDM_INTERFACE_RESOURCE_TAG}:{device_id}',
            ]
            for status_type, raw in (('admin', iface.get('admin')), ('oper', iface.get('oper'))):
                if raw is None:
                    continue
                self.gauge('interface.status', 1 if raw else 0, tags=iface_tags + [f'status_type:{status_type}'])
            speed = _parse_speed(iface.get('speed'))
            if speed is not None:
                self.gauge('interface.speed', speed, tags=iface_tags)
            interfaces.append(create_interface_metadata(client.app_ip, iface, namespace))
        self._submit_metadata(interfaces, collect_timestamp)

    def _collect_cpu_stats(self, client: ApplianceClient, base_tags: list[str], newest: int) -> None:
        cpu_data = client.get_cpu_stats(newest)
        if not cpu_data:
            return
        buckets = cpu_data.get('data') or []
        if not buckets:
            return
        latest_ts = cpu_data.get('latestTimestamp')
        bucket = next((b for b in buckets if str(latest_ts) in b), buckets[-1])
        entries = next(iter(bucket.values()), [])
        aggregate = next((e for e in entries if str(e.get('cpu_number')).upper() == 'ALL'), None)
        if aggregate is None:
            self.log.warning("No aggregate CPU data found for appliance %s", client.app_ip)
            return
        for state, field in _CPU_STATE_FIELDS.items():
            value = aggregate.get(field)
            if value is None:
                continue
            try:
                self.gauge('device.cpu.usage', float(value), tags=base_tags + [f'cpu_state:{state}'])
            except (TypeError, ValueError):
                continue

    def _collect_memory_stats(self, client: ApplianceClient, base_tags: list[str]) -> None:
        mem_data = client.get_memory_stats()
        if not isinstance(mem_data, dict):
            return
        for field in ('total', 'free', 'used', 'buffers', 'cached'):
            value = mem_data.get(field)
            if value is not None:
                self.gauge('device.memory.usage', value * 1024, tags=base_tags + [f'memory_type:{field}'])

    def _collect_disk_stats(self, client: ApplianceClient, base_tags: list[str]) -> None:
        disk_data = client.get_disk_usage()
        if not isinstance(disk_data, dict):
            return
        for mount, entry in disk_data.items():
            if not isinstance(entry, dict):
                continue
            filesystem = entry.get('filesystem')
            if filesystem in (None, 'none', 'tmpfs'):
                continue
            mount_tags = base_tags + [f'mount:{mount}', f'device:{filesystem}']
            used_kb = entry.get('used')
            available_kb = entry.get('available')
            if used_kb is not None:
                self.gauge('device.disk.usage', used_kb * 1024, tags=mount_tags + ['disk_type:used'])
            if available_kb is not None:
                self.gauge('device.disk.usage', available_kb * 1024, tags=mount_tags + ['disk_type:free'])

    def _collect_system_info(self, client: ApplianceClient, base_tags: list[str]) -> None:
        info = client.get_system_info()
        if not isinstance(info, dict):
            return
        uptime_ms = info.get('uptime')
        if uptime_ms is None:
            self.log.warning("No uptime found for appliance %s", client.app_ip)
            return
        try:
            self.gauge('device.uptime', float(uptime_ms) / 1000.0, tags=base_tags)
        except (TypeError, ValueError):
            return

    def _collect_alarm_stats(self, client: ApplianceClient, base_tags: list[str]) -> None:
        alarms = client.get_alarms()
        hw_alarm = False
        if isinstance(alarms, dict) and isinstance(alarms.get('outstanding'), list):
            hw_alarm = any(a.get('type') == 'HW' for a in alarms['outstanding'])
        if hw_alarm:
            self.log.debug("Hardware alarm detected on appliance %s", client.app_ip)
        self.gauge('device.hardware.ok', 0 if hw_alarm else 1, tags=base_tags)


_SPEED_RE = re.compile(r'^(\d+)\s*(Mb/s|Gb/s|Kb/s)', re.IGNORECASE)

_SPEED_MULTIPLIERS = {
    'kb/s': 1_000,
    'mb/s': 1_000_000,
    'gb/s': 1_000_000_000,
}


def _parse_speed(value: Any) -> float | None:
    """Parse interface speed to bits per second."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = _SPEED_RE.match(str(value))
    if m:
        return float(m.group(1)) * _SPEED_MULTIPLIERS[m.group(2).lower()]
    return None
