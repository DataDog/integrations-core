# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import ipaddress
import json
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import RequestsWrapper

from .appliance_models import Appliance, Appliances
from .client import ApplianceClient, OrchestratorClient
from .config_models import ConfigMixin
from .constants import (
    ALARM_SEVERITY_BY_ID,
    ALARM_SEVERITY_TO_ALERT_TYPE,
    CPU_STATE_FIELDS,
    MINUTE_STATS_INTERVAL,
    NDM_INTERFACE_RESOURCE_TAG,
)
from .metrics_store import MetricsStore
from .minute_stats import MinuteStats, TunnelV2Stats
from .ndm_models import (
    DeviceMetadata,
    InterfaceMetadata,
    TunnelMetadata,
    batch_payloads,
    create_device_metadata,
    create_interface_metadata,
    create_tunnel_metadata,
)
from .utils import parse_speed


class HpeArubaEdgeconnectCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'hpe_aruba_edgeconnect'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.http.persist_connections = True
        self._peer_lookup: dict[str, tuple[str, str]] = {}
        self._overlay_map: dict[str, str] = {}
        self._traffic_class_map: dict[str, str] = {}
        self._appliance_clients: dict[str, ApplianceClient] = {}
        self._orch_client: OrchestratorClient | None = None
        self._appliance_clients_lock = threading.Lock()
        self.check_initializations.append(self._parse_config)

    def _parse_config(self) -> None:
        self.tags = list(self.config.tags or []) + [f'orch_ip:{self.config.orchestrator_ip}']
        self.namespace = self.config.namespace or 'default'
        self.max_backfill = self.config.max_backfill_minutes or 5

    def _get_orch_client(self) -> OrchestratorClient:
        if self._orch_client is not None:
            return self._orch_client
        client = OrchestratorClient(self.http, self.config.orchestrator_ip)
        client.login(self.config.orchestrator_username, self.config.orchestrator_password)
        self._orch_client = client
        return client

    def check(self, _: Any) -> None:
        try:
            orch_client = self._get_orch_client()
        except Exception:
            self.gauge('orchestrator.reachability', 0, tags=self.tags)
            self._orch_client = None
            raise
        self.gauge('orchestrator.reachability', 1, tags=self.tags)
        appliances = self._collect_appliances_from_orch(orch_client)
        self._remove_stale_appliance_clients({ap.ip for ap in appliances})
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
                    with self._appliance_clients_lock:
                        self._appliance_clients.pop(ap.ip, None)
                    self.log.warning("Failed to collect from appliance %s", ap.ip, exc_info=True)

    def _remove_stale_appliance_clients(self, current_ips: set[str]) -> None:
        stale_ips = set(self._appliance_clients) - current_ips
        for ip in stale_ips:
            del self._appliance_clients[ip]

    def _submit_metadata(
        self,
        items: list[DeviceMetadata] | list[InterfaceMetadata] | list[TunnelMetadata],
        collect_timestamp: int | None = None,
    ) -> None:
        if not items or not self.config.send_ndm_metadata:
            return
        for batch in batch_payloads(self.namespace, items, collect_timestamp):
            self.event_platform_event(
                json.dumps(batch.model_dump(exclude_none=True)),
                "network-devices-metadata",
            )

    def _parse_appliances(self, raw_appliances: list[dict]) -> list[Appliance]:
        appliances = []
        for raw in raw_appliances:
            raw_ip = raw.get('ip', '')
            try:
                ipaddress.ip_address(raw_ip)
            except ValueError:
                self.log.warning(
                    "Skipping appliance with non-IP address %r from orchestrator %s",
                    raw_ip,
                    self.config.orchestrator_ip,
                )
                continue
            appliances.append(Appliance(raw))
        return appliances

    def _collect_appliances_from_orch(self, client: OrchestratorClient) -> Appliances:
        raw_appliances = client.get_appliances()
        if not raw_appliances:
            self.log.warning("No appliances returned from orchestrator %s", self.config.orchestrator_ip)
            return Appliances([], self.log)
        self.log.debug("Found %d appliances from orchestrator before filtering", len(raw_appliances))
        all_appliances = self._parse_appliances(raw_appliances)
        self._peer_lookup = {ap.host_name: (ap.ip, ap.site or 'unknown') for ap in all_appliances if ap.host_name}
        appliances = Appliances(all_appliances, self.log)
        appliances.filter(self.config.appliance_ips)
        self.log.debug("Monitoring %d appliances after filtering: %s", len(appliances), [ap.ip for ap in appliances])
        appliances.resolve_credentials(
            self.config.orchestrator_username,
            self.config.orchestrator_password,
            self.config.appliance_credentials_overrides,
        )
        namespace = self.namespace
        devices: list[DeviceMetadata] = []
        for ap in appliances:
            tags = self.tags + ap.tags(namespace)
            self.gauge('device.reachability', 1 if ap.is_reachable else 0, tags=tags)
            if self.config.send_ndm_metadata:
                devices.append(create_device_metadata(ap, namespace))
        if self.config.send_ndm_metadata:
            self._submit_metadata(devices)
        try:
            self._overlay_map, self._traffic_class_map = client.get_overlay_config()
        except Exception:
            self.log.warning(
                "Failed to fetch overlay config; tunnel and shaper metrics will be emitted without the "
                "overlay_name tag.",
                exc_info=True,
            )
            self._overlay_map = {}
            self._traffic_class_map = {}
        return appliances

    def _create_appliance_client(self, app_ip: str, username: str, password: str) -> ApplianceClient:
        cached = self._appliance_clients.get(app_ip)
        if cached is not None:
            return cached
        http = RequestsWrapper(self.instance or {}, self.init_config, self.HTTP_CONFIG_REMAPPER, self.log)
        http.persist_connections = True
        client = ApplianceClient(http, app_ip, self.log)
        client.login(username, password)
        with self._appliance_clients_lock:
            return self._appliance_clients.setdefault(app_ip, client)

    def _timestamps_to_fetch(self, app_ip: str, newest: int) -> list[int]:
        raw = self.read_persistent_cache(f'last_timestamp:{app_ip}')
        last_ts = int(raw) if raw else None

        if last_ts is not None and newest == last_ts:
            return []

        if last_ts is None:
            self.log.debug("First run for %s, collecting only the newest timestamp %d", app_ip, newest)
            return [newest]

        timestamps: list[int] = []
        ts = newest
        while ts > last_ts and len(timestamps) < self.max_backfill:
            timestamps.append(ts)
            ts -= MINUTE_STATS_INTERVAL

        if ts > last_ts:
            self.log.warning(
                "Appliance %s is %d minutes behind; capping backfill at %d minute(s). Older data will be skipped.",
                app_ip,
                (newest - last_ts) // MINUTE_STATS_INTERVAL,
                self.max_backfill,
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

    def _collect_minute_stats(
        self,
        client: ApplianceClient,
        app_ip: str,
        timestamps: list[int],
        base_tags: list[str],
        device_id: str,
        traffic_class_map: dict[str, str],
        overlay_map: dict[str, str],
    ) -> tuple[list[TunnelV2Stats], int | None]:
        store = MetricsStore()
        latest_tunnel_stats: list[TunnelV2Stats] = []
        latest_tunnel_stats_ts: int | None = None
        last_successful_ts: int | None = None
        contents: dict[int, bytes] = {}
        failed_ts: set[int] = set()
        max_dl = min(len(timestamps), 5)
        with ThreadPoolExecutor(max_workers=max_dl) as pool:
            dl_futs = {pool.submit(client.get_minute_stats, f'st2-{ts}.tgz'): ts for ts in timestamps}
            for fut in as_completed(dl_futs):
                ts = dl_futs[fut]
                try:
                    contents[ts] = fut.result()
                except Exception:
                    self.log.warning(
                        "Failed to download minute-stats archive st2-%d.tgz for appliance %s, skipping",
                        ts,
                        app_ip,
                        exc_info=True,
                    )
                    failed_ts.add(ts)
        for ts in reversed(timestamps):
            if ts in failed_ts:
                continue
            try:
                minute_stats = MinuteStats(contents[ts], app_ip, ts, self.log)
                minute_stats.record(store, base_tags, device_id, traffic_class_map, overlay_map)
            except Exception:
                self.log.warning(
                    "Failed to process minute-stats archive st2-%d.tgz for appliance %s, skipping",
                    ts,
                    app_ip,
                    exc_info=True,
                )
                continue
            last_successful_ts = ts
            if minute_stats.tunnels:
                latest_tunnel_stats = minute_stats.tunnels
                latest_tunnel_stats_ts = ts
        store.flush(self)
        if last_successful_ts is not None:
            self.write_persistent_cache(f'last_timestamp:{app_ip}', str(last_successful_ts))
        return latest_tunnel_stats, latest_tunnel_stats_ts

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

        namespace = self.namespace
        base_tags = self.tags + appliance.tags(namespace)
        device_id = appliance.device_id(namespace)
        newest = client.get_newest_timestamp()

        timestamps = self._timestamps_to_fetch(app_ip, newest)
        if timestamps:
            latest_tunnel_stats, latest_tunnel_stats_ts = self._collect_minute_stats(
                client, app_ip, timestamps, base_tags, device_id, traffic_class_map, overlay_map
            )
        else:
            latest_tunnel_stats = []
            latest_tunnel_stats_ts = None
            self.log.debug("Appliance %s stats are up to date (last timestamp: %d)", app_ip, newest)

        collectors: list[tuple[str, Callable[[], None]]] = [
            ('network_interfaces', lambda: self._collect_network_interfaces(client, base_tags, device_id, newest)),
            ('cpu_stats', lambda: self._collect_cpu_stats(client, base_tags, newest)),
            ('memory_stats', lambda: self._collect_memory_stats(client, base_tags)),
            ('disk_stats', lambda: self._collect_disk_stats(client, base_tags)),
            ('alarm_stats', lambda: self._collect_alarm_stats(client, base_tags)),
            ('system_info', lambda: self._collect_system_info(client, base_tags)),
        ]
        if latest_tunnel_stats and latest_tunnel_stats_ts and self.config.send_ndm_metadata:
            collectors.append(
                (
                    'tunnel_metadata',
                    lambda: self._collect_tunnel_metadata(
                        client,
                        appliance,
                        latest_tunnel_stats,
                        peer_lookup,
                        overlay_map,
                        namespace,
                        latest_tunnel_stats_ts,
                    ),
                )
            )
        max_workers = min(len(collectors), self.config.max_concurrency or len(collectors))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = {pool.submit(fn): name for name, fn in collectors}
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception:
                    self.log.warning("Collection step %s failed for appliance %s", futs[f], app_ip, exc_info=True)

    def _collect_tunnel_metadata(
        self,
        client: ApplianceClient,
        appliance: Appliance,
        tunnel_stats: list[TunnelV2Stats],
        peer_lookup: dict[str, tuple[str, str]],
        overlay_map: dict[str, str],
        namespace: str,
        collect_timestamp: int,
    ) -> None:
        wan_labels: set[str] = set()
        try:
            labels = client.get_interface_labels()
        except Exception:
            self.log.warning(
                "Failed to fetch interface labels for appliance %s; "
                "tunnel_color will be empty for non-overlay tunnels.",
                appliance.ip,
                exc_info=True,
            )
        else:
            wan_entries = labels.get('wan') if isinstance(labels, dict) else None
            if isinstance(wan_entries, dict):
                wan_labels = {name for name in wan_entries.values() if isinstance(name, str) and name}
        tunnels: list[TunnelMetadata] = [
            create_tunnel_metadata(
                t,
                appliance.ip,
                appliance.site,
                namespace,
                peer_lookup,
                overlay_map,
                wan_labels,
                self.log,
            )
            for t in tunnel_stats
        ]
        self._submit_metadata(tunnels, collect_timestamp)

    def _collect_network_interfaces(
        self,
        client: ApplianceClient,
        base_tags: list[str],
        device_id: str,
        collect_timestamp: int,
    ) -> None:
        data = client.get_network_interfaces()
        namespace = self.namespace
        interfaces: list[InterfaceMetadata] = []
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
            speed = parse_speed(iface.get('speed'))
            if speed is not None:
                self.gauge('interface.speed', speed, tags=iface_tags)
            if self.config.send_ndm_metadata:
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
        entries: list[Any] = next(iter(bucket.values()), [])
        aggregate = next((e for e in entries if str(e.get('cpu_number')).upper() == 'ALL'), None)
        if aggregate is None:
            self.log.warning("No aggregate CPU data found for appliance %s", client.app_ip)
            return
        for state, field in CPU_STATE_FIELDS.items():
            value = aggregate.get(field)
            if value is None:
                continue
            try:
                cpu = float(value)
            except (TypeError, ValueError):
                self.log.warning(
                    "Failed to convert CPU %s value %s to float for appliance %s, skipping", state, value, client.app_ip
                )
                continue
            self.gauge('device.cpu.usage', cpu, tags=base_tags + [f'cpu_state:{state}'])

    def _collect_memory_stats(self, client: ApplianceClient, base_tags: list[str]) -> None:
        mem_data = client.get_memory_stats()
        if not isinstance(mem_data, dict):
            return
        total_raw = mem_data.get('total')
        used_raw = mem_data.get('used')
        if total_raw is None or used_raw is None:
            return
        try:
            total = float(total_raw)
            used = float(used_raw)
        except (TypeError, ValueError):
            return
        if total <= 0:
            return
        self.gauge('device.memory.usage', (used / total) * 100.0, tags=base_tags)

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
            used_percent = entry.get('usedpercent')
            if used_percent is None:
                continue
            try:
                value = float(used_percent)
            except (TypeError, ValueError):
                continue
            mount_tags = base_tags + [f'mount:{mount}', f'device:{filesystem}']
            self.gauge('device.disk.usage', value, tags=mount_tags)

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
        outstanding: list[dict[str, Any]] = []
        if isinstance(alarms, dict) and isinstance(alarms.get('outstanding'), list):
            outstanding = [a for a in alarms['outstanding'] if isinstance(a, dict)]
        hw_alarm = any(a.get('type') == 'HW' for a in outstanding)
        if hw_alarm:
            self.log.debug("Hardware alarm detected on appliance %s", client.app_ip)
        self.gauge('device.hardware.ok', 0 if hw_alarm else 1, tags=base_tags)
        if not self.config.collect_events:
            return
        cache_key = f'last_alarm_ts:{client.app_ip}'
        raw = self.read_persistent_cache(cache_key)
        last_ts = int(raw) if raw else 0
        newest_ts = last_ts
        for alarm in outstanding:
            raised_ms = alarm.get('time')
            if isinstance(raised_ms, (int, float)):
                if raised_ms <= last_ts:
                    continue
                newest_ts = max(newest_ts, int(raised_ms))
            self._submit_alarm_event(alarm, client.app_ip, base_tags)
        if newest_ts > last_ts:
            self.write_persistent_cache(cache_key, str(newest_ts))

    def _submit_alarm_event(self, alarm: dict[str, Any], app_ip: str, base_tags: list[str]) -> None:
        severity_id = alarm.get('severity')
        severity = ALARM_SEVERITY_BY_ID.get(severity_id, 'unknown') if isinstance(severity_id, int) else 'unknown'
        alert_type = ALARM_SEVERITY_TO_ALERT_TYPE.get(severity, 'info')
        description = alarm.get('description') or alarm.get('name') or 'Alarm'
        recommendation = alarm.get('recommendation')
        msg_text = f'{description}\n\nRecommendation: {recommendation}' if recommendation else description
        tags = base_tags + [
            f'alarm_severity:{severity}',
            f'alarm_source:{alarm.get("source", "unknown")}',
            f'alarm_name:{alarm.get("name", "unknown")}',
        ]
        event: dict[str, Any] = {
            'event_type': alarm.get("type", "unknown"),
            'source_type_name': self.__NAMESPACE__,
            'msg_title': f'[HPE Aruba EdgeConnect] {severity.capitalize()}: {description}',
            'msg_text': msg_text,
            'alert_type': alert_type,
            'tags': tags,
        }
        sequence_id = alarm.get('sequenceId')
        if sequence_id is not None:
            event['aggregation_key'] = f'{app_ip}:{sequence_id}'
        raised_ms = alarm.get('time')
        if isinstance(raised_ms, (int, float)):
            event['timestamp'] = int(raised_ms / 1000)
        self.event(event)
