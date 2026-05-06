# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import tarfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar

from datadog_checks.hpe_aruba_edgeconnect.metrics_store import MetricsStore
from datadog_checks.hpe_aruba_edgeconnect.parsers.appperf import AppperfStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.dscp import DscpPeakStats, DscpStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.interface import (
    InterfaceOverlayStats,
    InterfacePeakStats,
    InterfaceStats,
)
from datadog_checks.hpe_aruba_edgeconnect.parsers.probe import ProbeStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.shaper import ShaperStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.tunnel import (
    JitterStats,
    MosStats,
    TunnelAvailability,
    TunnelPeakStats,
    TunnelV2Stats,
)

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


@dataclass(init=False, slots=True)
class MinuteStats:
    """Represents the contents of a per-appliance minute-stats .tgz archive."""

    FILES_NEEDED: ClassVar[frozenset[str]] = frozenset(
        [
            'interface.csv',
            'interface_peak.csv',
            'tunnel_v2.txt',
            'tunnel_peak.csv',
            'jitter.csv',
            'mos.csv',
            'dscp.csv',
            'dscp_peak.csv',
            'tunnel_availability_v2.txt',
            'interface_overlay.csv',
            'probe_v2.txt',
            'shaper.csv',
            'appperf_v2.txt',
        ]
    )

    appliance_ip: str
    timestamp: int
    interfaces: list[InterfaceStats]
    interface_peaks: list[InterfacePeakStats]
    tunnels: list[TunnelV2Stats]
    tunnel_peaks: list[TunnelPeakStats]
    jitter: list[JitterStats]
    mos: list[MosStats]
    dscp: list[DscpStats]
    dscp_peaks: list[DscpPeakStats]
    tunnel_availability: list[TunnelAvailability]
    interface_overlays: list[InterfaceOverlayStats]
    probes: list[ProbeStats]
    shaper: list[ShaperStats]
    appperf: list[AppperfStats]
    files: dict[str, str]
    _log: CheckLoggingAdapter

    def __init__(self, data: bytes, appliance_ip: str, timestamp: int, logger: CheckLoggingAdapter) -> None:
        self.appliance_ip = appliance_ip
        self.timestamp = timestamp
        self._log = logger

        self.files = {}
        with tarfile.open(fileobj=BytesIO(data), mode='r:gz') as tf:
            for member in tf.getmembers():
                basename = os.path.basename(member.name)
                if basename not in self.FILES_NEEDED:
                    continue
                f = tf.extractfile(member)
                if f is None:
                    continue
                self.files[basename] = f.read().decode('utf-8')

        self._log.debug(
            "Parsing minute-stats archive for %s at timestamp %d (%d files found)",
            appliance_ip,
            timestamp,
            len(self.files),
        )
        for required_file in self.FILES_NEEDED:
            if required_file not in self.files:
                self._log.warning(
                    "File %s not found in archive for appliance %s at timestamp %d",
                    required_file,
                    appliance_ip,
                    timestamp,
                )

        self.interfaces = self._safe_parse(
            'interface.csv', lambda: InterfaceStats.parse(self.get('interface.csv'), self._log)
        )
        self.interface_peaks = self._safe_parse(
            'interface_peak.csv', lambda: InterfacePeakStats.parse(self.get('interface_peak.csv'), self._log)
        )
        self.tunnels = self._safe_parse('tunnel_v2.txt', lambda: TunnelV2Stats.parse(self.get('tunnel_v2.txt')))
        self.tunnel_peaks = self._safe_parse(
            'tunnel_peak.csv', lambda: TunnelPeakStats.parse(self.get('tunnel_peak.csv'))
        )
        self.jitter = self._safe_parse('jitter.csv', lambda: JitterStats.parse(self.get('jitter.csv')))
        self.mos = self._safe_parse('mos.csv', lambda: MosStats.parse(self.get('mos.csv')))
        self.dscp = self._safe_parse('dscp.csv', lambda: DscpStats.parse(self.get('dscp.csv')))
        self.dscp_peaks = self._safe_parse('dscp_peak.csv', lambda: DscpPeakStats.parse(self.get('dscp_peak.csv')))
        self.tunnel_availability = self._safe_parse(
            'tunnel_availability_v2.txt', lambda: TunnelAvailability.parse(self.get('tunnel_availability_v2.txt'))
        )
        self.interface_overlays = self._safe_parse(
            'interface_overlay.csv', lambda: InterfaceOverlayStats.parse(self.get('interface_overlay.csv'))
        )
        self.probes = self._safe_parse('probe_v2.txt', lambda: ProbeStats.parse(self.get('probe_v2.txt')))
        self.shaper = self._safe_parse('shaper.csv', lambda: ShaperStats.parse(self.get('shaper.csv')))
        self.appperf = self._safe_parse('appperf_v2.txt', lambda: AppperfStats.parse(self.get('appperf_v2.txt')))

    def _safe_parse[T](self, filename: str, parser: Callable[[], Iterator[T]]) -> list[T]:
        try:
            return list(parser())
        except Exception:
            self._log.exception(
                "Failed to parse %s for appliance %s at timestamp %d; skipping this file",
                filename,
                self.appliance_ip,
                self.timestamp,
            )
            return []

    def get(self, filename: str) -> str:
        return self.files.get(filename, '')

    def record(self, store: MetricsStore, base_tags: list[str], device_id: str) -> None:
        self._record_interface_stats(store, base_tags, device_id)
        self._record_tunnel_stats(store, base_tags)
        self._record_tunnel_availability_stats(store, base_tags)
        self._record_internet_breakout_stats(store, base_tags, device_id)
        self._record_probe_stats(store, base_tags)
        self._record_shaper_stats(store, base_tags)
        self._record_appperf_stats(store, base_tags)
        self._record_dscp_stats(store, base_tags)

    def _record_interface_stats(self, store: MetricsStore, base_tags: list[str], device_id: str) -> None:
        iface_max_bw: dict[str, tuple[float, float]] = {}
        for iface in self.interfaces:
            iface.record(store, base_tags, device_id)
            iface_max_bw[iface.ifname] = (iface.max_bw_tx, iface.max_bw_rx)
        for peak in self.interface_peaks:
            peak.record(store, base_tags, device_id, iface_max_bw.get(peak.ifname, (0.0, 0.0)))

    def _record_tunnel_stats(self, store: MetricsStore, base_tags: list[str]) -> None:
        tunnel_tags_by_alias: dict[str, list[str]] = {}
        for tun in self.tunnels:
            tunnel_tags_by_alias[tun.tunnel_alias] = tun.record(store, base_tags)
        for peak in self.tunnel_peaks:
            peak.record(store, base_tags, tunnel_tags_by_alias.get(peak.tunname, []))
        for jitter in self.jitter:
            tags = base_tags + [f'tunnel_name:{jitter.tunnel}'] + tunnel_tags_by_alias.get(jitter.tunnel, [])
            jitter.record(store, tags)
        for mos in self.mos:
            tags = base_tags + [f'tunnel_name:{mos.tunnel}'] + tunnel_tags_by_alias.get(mos.tunnel, [])
            mos.record(store, tags)

    def _record_tunnel_availability_stats(self, store: MetricsStore, base_tags: list[str]) -> None:
        for row in self.tunnel_availability:
            row.record(store, base_tags)

    def _record_internet_breakout_stats(self, store: MetricsStore, base_tags: list[str], device_id: str) -> None:
        for row in self.interface_overlays:
            row.record(store, base_tags, device_id)

    def _record_probe_stats(self, store: MetricsStore, base_tags: list[str]) -> None:
        for row in self.probes:
            row.record(store, base_tags)

    def _record_shaper_stats(self, store: MetricsStore, base_tags: list[str]) -> None:
        for row in self.shaper:
            row.record(store, base_tags)

    def _record_appperf_stats(self, store: MetricsStore, base_tags: list[str]) -> None:
        for row in self.appperf:
            row.record(store, base_tags)

    def _record_dscp_stats(self, store: MetricsStore, base_tags: list[str]) -> None:
        for dscp in self.dscp:
            dscp.record(store, base_tags)
        for peak in self.dscp_peaks:
            peak.record(store, base_tags)
