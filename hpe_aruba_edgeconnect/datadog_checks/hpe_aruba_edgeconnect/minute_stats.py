# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import csv
import os
import re
import tarfile
from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol

from datadog_checks.hpe_aruba_edgeconnect.constants import (
    APPPERF_COL_APP_DELAY,
    APPPERF_COL_APP_NAME,
    APPPERF_COL_CND_DELAY,
    APPPERF_COL_SND_DELAY,
    APPPERF_COL_TRANSPORT_TYPE,
    APPPERF_COL_TUNNEL_NAME,
    MINUTE_STATS_INTERVAL,
    NDM_INTERFACE_RESOURCE_TAG,
    PROBE_COL_ADMIN_UP,
    PROBE_COL_AVG_JITTER,
    PROBE_COL_AVG_LATENCY,
    PROBE_COL_AVG_LOSS,
    PROBE_COL_OPER_UP,
    PROBE_COL_PROBE_NAME,
    TUNNEL_AVAIL_COL_ALIAS,
    TUNNEL_AVAIL_COL_COLOR,
    TUNNEL_AVAIL_COL_SECONDS_DOWN,
    TUNNEL_AVAIL_COL_TUNNEL_ID,
    TUNNEL_TYPE_INTERNET_BREAKOUT,
    TUNNEL_V2_COL_ALIAS,
    TUNNEL_V2_COL_BYTES_LAN_RX,
    TUNNEL_V2_COL_BYTES_LAN_TX,
    TUNNEL_V2_COL_BYTES_WAN_RX,
    TUNNEL_V2_COL_BYTES_WAN_TX,
    TUNNEL_V2_COL_IS_SDWAN,
    TUNNEL_V2_COL_LATENCY_AVG,
    TUNNEL_V2_COL_LATENCY_MIN,
    TUNNEL_V2_COL_LOSS_PCT_POSTFEC,
    TUNNEL_V2_COL_LOSS_PCT_PREFEC,
    TUNNEL_V2_COL_OVERLAY_ID,
    TUNNEL_V2_COL_PKTS_LAN_RX,
    TUNNEL_V2_COL_PKTS_LAN_TX,
    TUNNEL_V2_COL_PKTS_WAN_RX,
    TUNNEL_V2_COL_PKTS_WAN_TX,
    TUNNEL_V2_COL_TUNNEL_ID,
)
from datadog_checks.hpe_aruba_edgeconnect.metrics_store import AggType, MetricsStore

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


_TUNNEL_ALIAS_RE = re.compile(r'^to_(.+)_(\w+-\w+)$')


_TUNNEL_AGGREGATE_ALIASES = frozenset({'all traffic', 'optimized traffic', 'pass-through', 'pass-through-unshaped'})


def _nonzero(raw: str | None) -> bool:
    if raw is None:
        return False
    try:
        return float(raw) != 0
    except ValueError:
        return False


def parse_tunnel_alias(alias: str) -> tuple[str, str]:
    """Extract ``(peer_hostname, wan_labels)`` from a tunnel alias of the form ``to_<peer>_<color>``.

    Returns ``('', '')`` when the alias does not match the expected pattern.
    """
    m = _TUNNEL_ALIAS_RE.match(alias)
    if m:
        return m.group(1), m.group(2)
    return '', ''


@dataclass(init=False, slots=True)
class TunnelV2Stats:
    tunnel_id: str
    tunnel_alias: str
    overlay_id: str
    is_sdwan: Literal['true', 'false', 'unknown']
    bytes_wan_tx: float | None
    bytes_wan_rx: float | None
    bytes_lan_tx: float | None
    bytes_lan_rx: float | None
    pkts_wan_tx: float | None
    pkts_wan_rx: float | None
    pkts_lan_tx: float | None
    pkts_lan_rx: float | None
    latency: float | None
    latency_min: float | None
    loss_prefec: float | None
    loss_postfec: float | None

    def __init__(self, cols: list[str]) -> None:
        n = len(cols)
        self.tunnel_id = cols[TUNNEL_V2_COL_TUNNEL_ID] if n > TUNNEL_V2_COL_TUNNEL_ID else 'unknown'
        self.tunnel_alias = cols[TUNNEL_V2_COL_ALIAS] if n > TUNNEL_V2_COL_ALIAS else 'unknown'
        self.overlay_id = cols[TUNNEL_V2_COL_OVERLAY_ID] if n > TUNNEL_V2_COL_OVERLAY_ID else 'unknown'
        if n > TUNNEL_V2_COL_IS_SDWAN:
            self.is_sdwan = 'true' if cols[TUNNEL_V2_COL_IS_SDWAN] == '1' else 'false'
        else:
            self.is_sdwan = 'unknown'
        self.bytes_wan_tx = float(cols[TUNNEL_V2_COL_BYTES_WAN_TX]) if n > TUNNEL_V2_COL_BYTES_WAN_TX else None
        self.bytes_wan_rx = float(cols[TUNNEL_V2_COL_BYTES_WAN_RX]) if n > TUNNEL_V2_COL_BYTES_WAN_RX else None
        self.bytes_lan_tx = float(cols[TUNNEL_V2_COL_BYTES_LAN_TX]) if n > TUNNEL_V2_COL_BYTES_LAN_TX else None
        self.bytes_lan_rx = float(cols[TUNNEL_V2_COL_BYTES_LAN_RX]) if n > TUNNEL_V2_COL_BYTES_LAN_RX else None
        self.pkts_wan_tx = float(cols[TUNNEL_V2_COL_PKTS_WAN_TX]) if n > TUNNEL_V2_COL_PKTS_WAN_TX else None
        self.pkts_wan_rx = float(cols[TUNNEL_V2_COL_PKTS_WAN_RX]) if n > TUNNEL_V2_COL_PKTS_WAN_RX else None
        self.pkts_lan_tx = float(cols[TUNNEL_V2_COL_PKTS_LAN_TX]) if n > TUNNEL_V2_COL_PKTS_LAN_TX else None
        self.pkts_lan_rx = float(cols[TUNNEL_V2_COL_PKTS_LAN_RX]) if n > TUNNEL_V2_COL_PKTS_LAN_RX else None
        self.latency = float(cols[TUNNEL_V2_COL_LATENCY_AVG]) / 100 if n > TUNNEL_V2_COL_LATENCY_AVG else None
        self.latency_min = float(cols[TUNNEL_V2_COL_LATENCY_MIN]) / 100 if n > TUNNEL_V2_COL_LATENCY_MIN else None
        self.loss_prefec = (
            float(cols[TUNNEL_V2_COL_LOSS_PCT_PREFEC]) / 100 if n > TUNNEL_V2_COL_LOSS_PCT_PREFEC else None
        )
        self.loss_postfec = (
            float(cols[TUNNEL_V2_COL_LOSS_PCT_POSTFEC]) / 100 if n > TUNNEL_V2_COL_LOSS_PCT_POSTFEC else None
        )

    def record(self, store: MetricsStore, base_tags: list[str], overlay_map: dict[str, str] | None = None) -> list[str]:
        """Records tunnel metrics and returns the extra tags for cross-referencing."""
        extra_tags = [f'tunnel_alias:{self.tunnel_alias}', f'is_sdwan:{self.is_sdwan}']
        if overlay_map:
            extra_tags.append(f'overlay_name:{overlay_map.get(self.overlay_id, self.overlay_id)}')
        base_tunnel_tags = base_tags + [f'tunnel_name:{self.tunnel_id}'] + extra_tags
        for side, bytes_tx, bytes_rx, pkts_tx, pkts_rx in [
            ('wan', self.bytes_wan_tx, self.bytes_wan_rx, self.pkts_wan_tx, self.pkts_wan_rx),
            ('lan', self.bytes_lan_tx, self.bytes_lan_rx, self.pkts_lan_tx, self.pkts_lan_rx),
        ]:
            tags = base_tunnel_tags + [f'side:{side}']
            store.record('tunnel.throughput.tx.bytes.count', bytes_tx, tags, AggType.SUM)
            store.record('tunnel.throughput.rx.bytes.count', bytes_rx, tags, AggType.SUM)
            store.record('tunnel.throughput.tx.packets.count', pkts_tx, tags, AggType.SUM)
            store.record('tunnel.throughput.rx.packets.count', pkts_rx, tags, AggType.SUM)
            if bytes_tx is not None:
                store.record('tunnel.throughput.tx.bytes.rate', bytes_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
            if bytes_rx is not None:
                store.record('tunnel.throughput.rx.bytes.rate', bytes_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
            if pkts_tx is not None:
                store.record('tunnel.throughput.tx.packets.rate', pkts_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
            if pkts_rx is not None:
                store.record('tunnel.throughput.rx.packets.rate', pkts_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
        store.record('tunnel.latency', self.latency, base_tunnel_tags, AggType.AVG)
        store.record('tunnel.latency.min', self.latency_min, base_tunnel_tags, AggType.MIN)
        store.record('tunnel.loss', self.loss_postfec, base_tunnel_tags + ['fec:post'], AggType.AVG)
        store.record('tunnel.loss', self.loss_prefec, base_tunnel_tags + ['fec:pre'], AggType.AVG)
        return extra_tags

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[TunnelV2Stats]:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            stat = cls(line.split(','))
            if stat.tunnel_id in _TUNNEL_AGGREGATE_ALIASES and stat.tunnel_id == stat.tunnel_alias:
                continue
            yield stat


@dataclass(init=False, slots=True)
class TunnelPeakStats:
    tunname: str
    peak_bytes_wan_tx: float | None
    peak_bytes_wan_rx: float | None
    peak_bytes_lan_tx: float | None
    peak_bytes_lan_rx: float | None
    peak_pkts_wan_tx: float | None
    peak_pkts_wan_rx: float | None
    peak_pkts_lan_tx: float | None
    peak_pkts_lan_rx: float | None
    peak_latency: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.tunname = v.strip() if (v := row.get('tunname')) is not None else "unknown"
        self.peak_bytes_wan_tx = float(v) if (v := row.get('bytes_wtx')) is not None else None
        self.peak_bytes_wan_rx = float(v) if (v := row.get('bytes_wrx')) is not None else None
        self.peak_bytes_lan_tx = float(v) if (v := row.get('bytes_ltx')) is not None else None
        self.peak_bytes_lan_rx = float(v) if (v := row.get('bytes_lrx')) is not None else None
        self.peak_pkts_wan_tx = float(v) if (v := row.get('pkts_wtx')) is not None else None
        self.peak_pkts_wan_rx = float(v) if (v := row.get('pkts_wrx')) is not None else None
        self.peak_pkts_lan_tx = float(v) if (v := row.get('pkts_ltx')) is not None else None
        self.peak_pkts_lan_rx = float(v) if (v := row.get('pkts_lrx')) is not None else None
        self.peak_latency = float(v) / 100 if (v := row.get('latency_s')) is not None else None

    def record(self, store: MetricsStore, base_tags: list[str], extra_tags: list[str]) -> None:
        base_tunnel_tags = base_tags + [f'tunnel_name:{self.tunname}'] + extra_tags
        for side, bytes_tx, bytes_rx, pkts_tx, pkts_rx in [
            ('wan', self.peak_bytes_wan_tx, self.peak_bytes_wan_rx, self.peak_pkts_wan_tx, self.peak_pkts_wan_rx),
            ('lan', self.peak_bytes_lan_tx, self.peak_bytes_lan_rx, self.peak_pkts_lan_tx, self.peak_pkts_lan_rx),
        ]:
            if bytes_tx is None and bytes_rx is None:
                continue
            tags = base_tunnel_tags + [f'side:{side}']
            if bytes_tx is not None:
                store.record('tunnel.throughput.tx.bytes.max', bytes_tx, tags, AggType.MAX)
            if bytes_rx is not None:
                store.record('tunnel.throughput.rx.bytes.max', bytes_rx, tags, AggType.MAX)
            if pkts_tx is not None:
                store.record('tunnel.throughput.tx.packets.max', pkts_tx, tags, AggType.MAX)
            if pkts_rx is not None:
                store.record('tunnel.throughput.rx.packets.max', pkts_rx, tags, AggType.MAX)
        if self.peak_latency is not None:
            store.record('tunnel.latency.max', self.peak_latency, base_tunnel_tags, AggType.MAX)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[TunnelPeakStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if row.get('tunname', '').strip() in _TUNNEL_AGGREGATE_ALIASES:
                continue
            yield cls(row)


@dataclass(init=False, slots=True)
class JitterStats:
    tunnel: str
    jitter: float | None
    peak_jitter: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.tunnel = v.strip() if (v := row.get('tunnel')) is not None else "unknown"
        self.jitter = float(v) if (v := row.get(' jitter') or row.get('jitter')) is not None else None
        self.peak_jitter = float(v) if (v := row.get(' peak_jitter') or row.get('peak_jitter')) is not None else None

    def record(self, store: MetricsStore, tags: list[str]) -> None:
        store.record('tunnel.jitter', self.jitter, tags, AggType.AVG)
        store.record('tunnel.jitter.max', self.peak_jitter, tags, AggType.MAX)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[JitterStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            yield cls(row)


@dataclass(init=False, slots=True)
class MosStats:
    tunnel: str
    mos_postfec: float | None
    mos_prefec: float | None
    min_mos_postfec: float | None
    min_mos_prefec: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.tunnel = v.strip() if (v := row.get('tunnel')) is not None else "unknown"
        self.mos_postfec = float(v) if (v := row.get(' mos_postfec')) is not None else None
        self.mos_prefec = float(v) if (v := row.get(' mos_prefec')) is not None else None
        self.min_mos_postfec = float(v) if (v := row.get(' min_mos_postfec')) is not None else None
        self.min_mos_prefec = float(v) if (v := row.get(' min_mos_prefec')) is not None else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        store.record('tunnel.qoe.mos', self.mos_postfec, base_tags + ['fec:post'], AggType.AVG)
        store.record('tunnel.qoe.mos', self.mos_prefec, base_tags + ['fec:pre'], AggType.AVG)
        store.record('tunnel.qoe.mos.min', self.min_mos_postfec, base_tags + ['fec:post'], AggType.MIN)
        store.record('tunnel.qoe.mos.min', self.min_mos_prefec, base_tags + ['fec:pre'], AggType.MIN)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[MosStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            yield cls(row)


@dataclass(init=False, slots=True)
class TunnelAvailability:
    tunnel_id: str
    alias: str
    seconds_down: float | None
    color: str
    peer: str | None

    def __init__(self, cols: list[str]) -> None:
        n = len(cols)
        self.tunnel_id = cols[TUNNEL_AVAIL_COL_TUNNEL_ID] if n > TUNNEL_AVAIL_COL_TUNNEL_ID else 'unknown'
        self.alias = cols[TUNNEL_AVAIL_COL_ALIAS] if n > TUNNEL_AVAIL_COL_ALIAS else 'unknown'
        self.seconds_down = float(cols[TUNNEL_AVAIL_COL_SECONDS_DOWN]) if n > TUNNEL_AVAIL_COL_SECONDS_DOWN else None
        self.color = cols[TUNNEL_AVAIL_COL_COLOR] if n > TUNNEL_AVAIL_COL_COLOR else 'unknown'
        peer, _ = parse_tunnel_alias(self.alias)
        self.peer = peer or None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        tags = base_tags + [
            f'tunnel_name:{self.tunnel_id}',
            f'tunnel_alias:{self.alias}',
            f'tunnel_color:{self.color}',
        ]
        if self.peer is not None:
            tags.append(f'peer:{self.peer}')
        if self.seconds_down is not None:
            uptime_pct = max(0.0, (MINUTE_STATS_INTERVAL - self.seconds_down) / MINUTE_STATS_INTERVAL * 100)
            store.record('tunnel.availability', uptime_pct, tags, AggType.AVG)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[TunnelAvailability]:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            stat = cls(line.split(','))
            if stat.tunnel_id in _TUNNEL_AGGREGATE_ALIASES and stat.tunnel_id == stat.alias:
                continue
            yield stat


@dataclass(init=False, slots=True)
class InterfaceStats:
    ifname: str
    bytes_tx: float | None
    bytes_rx: float | None
    fwdrops_bytes_tx: float | None
    fwdrops_bytes_rx: float | None
    fwdrops_pkts_tx: float | None
    fwdrops_pkts_rx: float | None
    max_bw_tx: float | None
    max_bw_rx: float | None
    traftype: str
    _log: CheckLoggingAdapter

    def __init__(self, row: dict[str, str], logger: CheckLoggingAdapter) -> None:
        self.ifname = v.strip() if (v := row.get('ifname')) is not None else "unknown"
        self.bytes_tx = float(v) if (v := row.get('bytes_tx')) is not None else None
        self.bytes_rx = float(v) if (v := row.get('bytes_rx')) is not None else None
        self.fwdrops_bytes_tx = float(v) if (v := row.get('fwdrops_bytes_tx')) is not None else None
        self.fwdrops_bytes_rx = float(v) if (v := row.get('fwdrops_bytes_rx')) is not None else None
        self.fwdrops_pkts_tx = float(v) if (v := row.get('fwdrops_pkts_tx')) is not None else None
        self.fwdrops_pkts_rx = float(v) if (v := row.get('fwdrops_pkts_rx')) is not None else None
        self.max_bw_tx = float(v) if (v := row.get('max_bw_tx')) is not None else None
        self.max_bw_rx = float(v) if (v := row.get('max_bw_rx')) is not None else None
        self.traftype = v.strip() if (v := row.get('traftype')) is not None else "unknown"
        self._log = logger

    def record(self, store: MetricsStore, base_tags: list[str], device_id: str) -> None:
        tags = base_tags + [
            f'interface_name:{self.ifname}',
            f'traffic_type:{self.traftype}',
            f'{NDM_INTERFACE_RESOURCE_TAG}:{device_id}',
        ]
        bw_tx = self.bytes_tx / MINUTE_STATS_INTERVAL if self.bytes_tx is not None else None
        bw_rx = self.bytes_rx / MINUTE_STATS_INTERVAL if self.bytes_rx is not None else None
        store.record('interface.bandwidth.tx.count', self.bytes_tx, tags, AggType.SUM)
        store.record('interface.bandwidth.rx.count', self.bytes_rx, tags, AggType.SUM)
        store.record('interface.bandwidth.tx.rate', bw_tx, tags, AggType.AVG)
        store.record('interface.bandwidth.rx.rate', bw_rx, tags, AggType.AVG)
        store.record('interface.drops.bytes.tx.count', self.fwdrops_bytes_tx, tags, AggType.SUM)
        store.record('interface.drops.bytes.rx.count', self.fwdrops_bytes_rx, tags, AggType.SUM)
        store.record('interface.drops.packets.tx.count', self.fwdrops_pkts_tx, tags, AggType.SUM)
        store.record('interface.drops.packets.rx.count', self.fwdrops_pkts_rx, tags, AggType.SUM)
        if self.fwdrops_bytes_tx is not None:
            store.record(
                'interface.drops.bytes.tx.rate', self.fwdrops_bytes_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG
            )
        if self.fwdrops_bytes_rx is not None:
            store.record(
                'interface.drops.bytes.rx.rate', self.fwdrops_bytes_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG
            )
        if self.fwdrops_pkts_tx is not None:
            store.record(
                'interface.drops.packets.tx.rate', self.fwdrops_pkts_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG
            )
        if self.fwdrops_pkts_rx is not None:
            store.record(
                'interface.drops.packets.rx.rate', self.fwdrops_pkts_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG
            )
        if not self.max_bw_tx or not self.max_bw_rx:
            self._log.warning(
                "Max bandwidth is not available for %s, skipping average utilization metrics", self.ifname
            )
        else:
            if bw_tx is not None:
                store.record('interface.utilization.tx.avg', bw_tx / self.max_bw_tx * 100, tags, AggType.AVG)
            if bw_rx is not None:
                store.record('interface.utilization.rx.avg', bw_rx / self.max_bw_rx * 100, tags, AggType.AVG)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter) -> Iterator[InterfaceStats]:
        rows = list(csv.DictReader(StringIO(content)))
        # Some appliances only populate max_bw on the `all traffic` row; fall back to it when a
        # per-type row has no max_bw of its own (missing or zero) so utilization stays computable.
        fallback_max_bw: dict[str, tuple[str | None, str | None]] = {}
        for row in rows:
            if row.get('traftype', '').strip() != 'all traffic':
                continue
            ifname = row.get('ifname', '').strip()
            if ifname:
                fallback_max_bw[ifname] = (row.get('max_bw_tx'), row.get('max_bw_rx'))
        for row in rows:
            if row.get('traftype', '').strip() == 'all traffic':
                continue
            fb_tx, fb_rx = fallback_max_bw.get(row.get('ifname', '').strip(), (None, None))
            if not _nonzero(row.get('max_bw_tx')) and _nonzero(fb_tx):
                row['max_bw_tx'] = fb_tx
            if not _nonzero(row.get('max_bw_rx')) and _nonzero(fb_rx):
                row['max_bw_rx'] = fb_rx
            yield cls(row, logger)


@dataclass(init=False, slots=True)
class InterfacePeakStats:
    ifname: str
    peak_bytes_tx: float | None
    peak_bytes_rx: float | None
    peak_fwdrops_pkts_tx: float | None
    peak_fwdrops_pkts_rx: float | None
    peak_fwdrops_bytes_tx: float | None
    peak_fwdrops_bytes_rx: float | None
    peak_max_bw_tx: float | None
    peak_max_bw_rx: float | None
    traftype: str
    _log: CheckLoggingAdapter

    def __init__(self, row: dict[str, str], logger: CheckLoggingAdapter) -> None:
        self.ifname = v.strip() if (v := row.get('ifname')) is not None else "unknown"
        self.peak_bytes_tx = float(v) if (v := row.get('bytes_tx')) is not None else None
        self.peak_bytes_rx = float(v) if (v := row.get('bytes_rx')) is not None else None
        self.peak_fwdrops_pkts_tx = float(v) if (v := row.get('fwdrops_pkts_tx')) is not None else None
        self.peak_fwdrops_pkts_rx = float(v) if (v := row.get('fwdrops_pkts_rx')) is not None else None
        self.peak_fwdrops_bytes_tx = float(v) if (v := row.get('fwdrops_bytes_tx')) is not None else None
        self.peak_fwdrops_bytes_rx = float(v) if (v := row.get('fwdrops_bytes_rx')) is not None else None
        self.peak_max_bw_tx = float(v) if (v := row.get('max_bw_tx')) is not None else None
        self.peak_max_bw_rx = float(v) if (v := row.get('max_bw_rx')) is not None else None
        self.traftype = v.strip() if (v := row.get('traftype')) is not None else "unknown"
        self._log = logger

    def record(
        self,
        store: MetricsStore,
        base_tags: list[str],
        device_id: str,
        max_bw: tuple[float | None, float | None],
    ) -> None:
        tags = base_tags + [
            f'interface_name:{self.ifname}',
            f'traffic_type:{self.traftype}',
            f'{NDM_INTERFACE_RESOURCE_TAG}:{device_id}',
        ]
        store.record('interface.bandwidth.tx.max', self.peak_bytes_tx, tags, AggType.MAX)
        store.record('interface.bandwidth.rx.max', self.peak_bytes_rx, tags, AggType.MAX)
        store.record('interface.drops.packets.tx.max', self.peak_fwdrops_pkts_tx, tags, AggType.MAX)
        store.record('interface.drops.packets.rx.max', self.peak_fwdrops_pkts_rx, tags, AggType.MAX)
        store.record('interface.drops.bytes.tx.max', self.peak_fwdrops_bytes_tx, tags, AggType.MAX)
        store.record('interface.drops.bytes.rx.max', self.peak_fwdrops_bytes_rx, tags, AggType.MAX)
        max_bw_tx, max_bw_rx = max_bw
        if not max_bw_tx or not max_bw_rx:
            self._log.warning("Max bandwidth is not available for %s, skipping peak utilization metrics", self.ifname)
            return
        if self.peak_bytes_tx is not None:
            peak_bw_tx = self.peak_bytes_tx / MINUTE_STATS_INTERVAL
            store.record('interface.utilization.tx.max', peak_bw_tx / max_bw_tx * 100, tags, AggType.MAX)
        if self.peak_bytes_rx is not None:
            peak_bw_rx = self.peak_bytes_rx / MINUTE_STATS_INTERVAL
            store.record('interface.utilization.rx.max', peak_bw_rx / max_bw_rx * 100, tags, AggType.MAX)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter) -> Iterator[InterfacePeakStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if row.get('traftype', '').strip() == 'all traffic':
                continue
            yield cls(row, logger)


@dataclass(init=False, slots=True)
class InterfaceOverlayStats:
    ifname: str
    bytes_tx: float | None
    bytes_rx: float | None
    max_bw_tx: float | None
    max_bw_rx: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.ifname = v.strip() if (v := row.get('ifname')) is not None else "unknown"
        self.bytes_tx = float(v) if (v := row.get('bytes_tx')) is not None else None
        self.bytes_rx = float(v) if (v := row.get('bytes_rx')) is not None else None
        self.max_bw_tx = float(v) if (v := row.get('max_bw_tx')) is not None else None
        self.max_bw_rx = float(v) if (v := row.get('max_bw_rx')) is not None else None

    def record(self, store: MetricsStore, base_tags: list[str], device_id: str) -> None:
        tags = base_tags + [
            f'interface_name:{self.ifname}',
            f'{NDM_INTERFACE_RESOURCE_TAG}:{device_id}',
        ]
        store.record('tunnel.internet_breakout.bandwidth.tx.count', self.bytes_tx, tags, AggType.SUM)
        store.record('tunnel.internet_breakout.bandwidth.rx.count', self.bytes_rx, tags, AggType.SUM)
        if self.bytes_tx is not None:
            store.record(
                'tunnel.internet_breakout.bandwidth.tx.rate', self.bytes_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG
            )
        if self.bytes_rx is not None:
            store.record(
                'tunnel.internet_breakout.bandwidth.rx.rate', self.bytes_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG
            )
        store.record('tunnel.internet_breakout.bandwidth.tx.max', self.max_bw_tx, tags, AggType.MAX)
        store.record('tunnel.internet_breakout.bandwidth.rx.max', self.max_bw_rx, tags, AggType.MAX)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[InterfaceOverlayStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if int(row.get('tuntype') or '0') != TUNNEL_TYPE_INTERNET_BREAKOUT:
                continue
            yield cls(row)


@dataclass(init=False, slots=True)
class DscpStats:
    dscp: str
    traftype: str
    bytes_wan_tx: float | None
    bytes_wan_rx: float | None
    bytes_lan_tx: float | None
    bytes_lan_rx: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.dscp = v.strip() if (v := row.get('dscp')) is not None else "unknown"
        self.traftype = v.strip() if (v := row.get('traftype')) is not None else "unknown"
        self.bytes_wan_tx = float(v) if (v := row.get('bytes_wtx')) is not None else None
        self.bytes_wan_rx = float(v) if (v := row.get('bytes_wrx')) is not None else None
        self.bytes_lan_tx = float(v) if (v := row.get('bytes_ltx')) is not None else None
        self.bytes_lan_rx = float(v) if (v := row.get('bytes_lrx')) is not None else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        dscp_tags = base_tags + [f'dscp:{self.dscp}', f'traffic_type:{self.traftype}']
        store.record('qos.class.bandwidth.tx.count', self.bytes_wan_tx, dscp_tags + ['side:wan'], AggType.SUM)
        store.record('qos.class.bandwidth.rx.count', self.bytes_wan_rx, dscp_tags + ['side:wan'], AggType.SUM)
        store.record('qos.class.bandwidth.tx.count', self.bytes_lan_tx, dscp_tags + ['side:lan'], AggType.SUM)
        store.record('qos.class.bandwidth.rx.count', self.bytes_lan_rx, dscp_tags + ['side:lan'], AggType.SUM)
        if self.bytes_wan_tx is not None:
            store.record(
                'qos.class.bandwidth.tx.rate',
                self.bytes_wan_tx / MINUTE_STATS_INTERVAL,
                dscp_tags + ['side:wan'],
                AggType.AVG,
            )
        if self.bytes_wan_rx is not None:
            store.record(
                'qos.class.bandwidth.rx.rate',
                self.bytes_wan_rx / MINUTE_STATS_INTERVAL,
                dscp_tags + ['side:wan'],
                AggType.AVG,
            )
        if self.bytes_lan_tx is not None:
            store.record(
                'qos.class.bandwidth.tx.rate',
                self.bytes_lan_tx / MINUTE_STATS_INTERVAL,
                dscp_tags + ['side:lan'],
                AggType.AVG,
            )
        if self.bytes_lan_rx is not None:
            store.record(
                'qos.class.bandwidth.rx.rate',
                self.bytes_lan_rx / MINUTE_STATS_INTERVAL,
                dscp_tags + ['side:lan'],
                AggType.AVG,
            )

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[DscpStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if row.get('traftype', '').strip() == 'all traffic':
                continue
            yield cls(row)


@dataclass(init=False, slots=True)
class DscpPeakStats:
    dscp: str
    traftype: str
    peak_bytes_wan_tx: float | None
    peak_bytes_wan_rx: float | None
    peak_bytes_lan_tx: float | None
    peak_bytes_lan_rx: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.dscp = v.strip() if (v := row.get('dscp')) is not None else "unknown"
        self.traftype = v.strip() if (v := row.get('traftype')) is not None else "unknown"
        self.peak_bytes_wan_tx = float(v) if (v := row.get('bytes_wtx')) is not None else None
        self.peak_bytes_wan_rx = float(v) if (v := row.get('bytes_wrx')) is not None else None
        self.peak_bytes_lan_tx = float(v) if (v := row.get('bytes_ltx')) is not None else None
        self.peak_bytes_lan_rx = float(v) if (v := row.get('bytes_lrx')) is not None else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        dscp_tags = base_tags + [f'dscp:{self.dscp}', f'traffic_type:{self.traftype}']
        wan_tags = dscp_tags + ['side:wan']
        store.record('qos.class.bandwidth.tx.max', self.peak_bytes_wan_tx, wan_tags, AggType.MAX)
        store.record('qos.class.bandwidth.rx.max', self.peak_bytes_wan_rx, wan_tags, AggType.MAX)
        lan_tags = dscp_tags + ['side:lan']
        store.record('qos.class.bandwidth.tx.max', self.peak_bytes_lan_tx, lan_tags, AggType.MAX)
        store.record('qos.class.bandwidth.rx.max', self.peak_bytes_lan_rx, lan_tags, AggType.MAX)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[DscpPeakStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if row.get('traftype', '').strip() == 'all traffic':
                continue
            yield cls(row)


@dataclass(init=False, slots=True)
class ProbeStats:
    probe_name: str
    avg_latency: float | None
    avg_loss: float | None
    avg_jitter: float | None
    admin_up: float | None
    oper_up: float | None

    def __init__(self, cols: list[str]) -> None:
        n = len(cols)
        self.probe_name = cols[PROBE_COL_PROBE_NAME] if n > PROBE_COL_PROBE_NAME else 'unknown'
        self.avg_latency = float(cols[PROBE_COL_AVG_LATENCY]) if n > PROBE_COL_AVG_LATENCY else None
        self.avg_loss = float(cols[PROBE_COL_AVG_LOSS]) if n > PROBE_COL_AVG_LOSS else None
        self.avg_jitter = float(cols[PROBE_COL_AVG_JITTER]) if n > PROBE_COL_AVG_JITTER else None
        self.admin_up = float(cols[PROBE_COL_ADMIN_UP]) if n > PROBE_COL_ADMIN_UP else None
        self.oper_up = float(cols[PROBE_COL_OPER_UP]) if n > PROBE_COL_OPER_UP else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        tags = base_tags + [f'probe_name:{self.probe_name}']
        store.record('circuit.sla.latency', self.avg_latency, tags, AggType.AVG)
        store.record('circuit.sla.loss', self.avg_loss, tags, AggType.AVG)
        store.record('circuit.sla.jitter', self.avg_jitter, tags, AggType.AVG)
        store.record('nexthop.status', self.admin_up, tags + ['status_type:admin'], AggType.LAST)
        store.record('nexthop.status', self.oper_up, tags + ['status_type:oper'], AggType.LAST)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[ProbeStats]:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            yield cls(line.split(','))


_SHAPER_DIRECTION_LABELS = {'0': 'outbound', '1': 'inbound'}


@dataclass(init=False, slots=True)
class ShaperStats:
    traffic_class: str
    direction: str
    qos_drops: float | None
    other_drops: float | None
    total_shaped_packets: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.traffic_class = v.strip() if (v := row.get('traffic_class')) is not None else "unknown"
        raw_direction = v.strip() if (v := row.get('direction')) is not None else "unknown"
        self.direction = _SHAPER_DIRECTION_LABELS.get(raw_direction, raw_direction)
        self.qos_drops = float(v) if (v := row.get('qos_drops')) is not None else None
        self.other_drops = float(v) if (v := row.get('other_drops')) is not None else None
        self.total_shaped_packets = float(v) if (v := row.get('shaped_packets')) is not None else None

    def record(
        self,
        store: MetricsStore,
        base_tags: list[str],
        traffic_class_map: dict[str, str] | None = None,
        logger: CheckLoggingAdapter | None = None,
    ) -> None:
        tags = base_tags + [f'direction:{self.direction}']
        if traffic_class_map:
            if self.traffic_class in traffic_class_map:
                overlay_name = traffic_class_map[self.traffic_class]
            else:
                overlay_name = self.traffic_class
                if logger is not None:
                    logger.debug(
                        "No overlay name mapping found for traffic class %s; falling back to raw id",
                        self.traffic_class,
                    )
            tags.append(f'overlay_name:{overlay_name}')
        store.record('qos.class.drops', self.qos_drops, tags + ['drop_type:qos'], AggType.SUM)
        store.record('qos.class.drops', self.other_drops, tags + ['drop_type:other'], AggType.SUM)
        if self.qos_drops is not None and self.total_shaped_packets is not None and self.total_shaped_packets > 0:
            store.record(
                'qos.class.drop.percentage', self.qos_drops / self.total_shaped_packets * 100, tags, AggType.AVG
            )

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[ShaperStats]:
        reader = csv.DictReader(StringIO(content), skipinitialspace=True)
        for row in reader:
            yield cls(row)


@dataclass(init=False, slots=True)
class AppperfStats:
    app_name: str
    tunnel_name: str
    transport_type: str
    cnd_delay: float | None
    snd_delay: float | None
    app_delay: float | None

    def __init__(self, cols: list[str]) -> None:
        n = len(cols)
        self.app_name = cols[APPPERF_COL_APP_NAME] if n > APPPERF_COL_APP_NAME else "unknown"
        self.tunnel_name = cols[APPPERF_COL_TUNNEL_NAME] if n > APPPERF_COL_TUNNEL_NAME else "unknown"
        self.transport_type = cols[APPPERF_COL_TRANSPORT_TYPE] if n > APPPERF_COL_TRANSPORT_TYPE else "unknown"
        self.cnd_delay = float(cols[APPPERF_COL_CND_DELAY]) if n > APPPERF_COL_CND_DELAY else None
        self.snd_delay = float(cols[APPPERF_COL_SND_DELAY]) if n > APPPERF_COL_SND_DELAY else None
        self.app_delay = float(cols[APPPERF_COL_APP_DELAY]) if n > APPPERF_COL_APP_DELAY else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        app_tags = base_tags + [f'application:{self.app_name}']
        if self.tunnel_name:
            app_tags = app_tags + [f'tunnel_name:{self.tunnel_name}']
        if self.transport_type:
            app_tags = app_tags + [f'transport_type:{self.transport_type}']
        for latency_type, value in [
            ('cnd', self.cnd_delay),
            ('snd', self.snd_delay),
            ('app', self.app_delay),
        ]:
            if value is not None:
                store.record('application.latency', value, app_tags + [f'latency_type:{latency_type}'], AggType.AVG)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[AppperfStats]:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            yield cls(line.split(','))


class _Parseable(Protocol):
    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter) -> Iterator: ...


@dataclass(init=False, slots=True)
class MinuteStats:
    """Represents the contents of a per-appliance minute-stats .tgz archive."""

    _PARSERS: ClassVar[list[tuple[str, str, type[_Parseable]]]] = [
        ('interface.csv', 'interfaces', InterfaceStats),
        ('interface_peak.csv', 'interface_peaks', InterfacePeakStats),
        ('tunnel_v2.txt', 'tunnels', TunnelV2Stats),
        ('tunnel_peak.csv', 'tunnel_peaks', TunnelPeakStats),
        ('jitter.csv', 'jitter', JitterStats),
        ('mos.csv', 'mos', MosStats),
        ('dscp.csv', 'dscp', DscpStats),
        ('dscp_peak.csv', 'dscp_peaks', DscpPeakStats),
        ('tunnel_availability_v2.txt', 'tunnel_availability', TunnelAvailability),
        ('interface_overlay.csv', 'interface_overlays', InterfaceOverlayStats),
        ('probe_v2.txt', 'probes', ProbeStats),
        ('shaper.csv', 'shaper', ShaperStats),
        ('appperf_v2.txt', 'appperf', AppperfStats),
    ]
    FILES_NEEDED: ClassVar[frozenset[str]] = frozenset(filename for filename, _, _ in _PARSERS)

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

        for filename, field_name, parser_cls in self._PARSERS:
            setattr(self, field_name, self._safe_parse(filename, parser_cls))

    def _safe_parse(self, filename: str, parser_cls: type[_Parseable]) -> list:
        try:
            return list(parser_cls.parse(self.get(filename), self._log))
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

    def record(
        self,
        store: MetricsStore,
        base_tags: list[str],
        device_id: str,
        traffic_class_map: dict[str, str] | None = None,
        overlay_map: dict[str, str] | None = None,
    ) -> None:
        self._record_interface_stats(store, base_tags, device_id)
        self._record_tunnel_stats(store, base_tags, overlay_map or {})
        self._record_tunnel_availability_stats(store, base_tags)
        self._record_internet_breakout_stats(store, base_tags, device_id)
        self._record_probe_stats(store, base_tags)
        self._record_shaper_stats(store, base_tags, traffic_class_map or {})
        self._record_appperf_stats(store, base_tags)
        self._record_dscp_stats(store, base_tags)

    def _record_interface_stats(self, store: MetricsStore, base_tags: list[str], device_id: str) -> None:
        iface_max_bw: dict[str, tuple[float | None, float | None]] = {}
        for iface in self.interfaces:
            iface.record(store, base_tags, device_id)
            iface_max_bw[iface.ifname] = (iface.max_bw_tx, iface.max_bw_rx)
        for peak in self.interface_peaks:
            peak.record(store, base_tags, device_id, iface_max_bw.get(peak.ifname, (None, None)))

    def _record_tunnel_stats(self, store: MetricsStore, base_tags: list[str], overlay_map: dict[str, str]) -> None:
        tunnel_tags_by_id: dict[str, list[str]] = {}
        for tun in self.tunnels:
            tunnel_tags_by_id[tun.tunnel_id] = tun.record(store, base_tags, overlay_map)
        for peak in self.tunnel_peaks:
            peak.record(store, base_tags, tunnel_tags_by_id.get(peak.tunname, []))
        for jitter in self.jitter:
            tags = base_tags + [f'tunnel_name:{jitter.tunnel}'] + tunnel_tags_by_id.get(jitter.tunnel, [])
            jitter.record(store, tags)
        for mos in self.mos:
            tags = base_tags + [f'tunnel_name:{mos.tunnel}'] + tunnel_tags_by_id.get(mos.tunnel, [])
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

    def _record_shaper_stats(
        self, store: MetricsStore, base_tags: list[str], traffic_class_map: dict[str, str]
    ) -> None:
        if self.shaper and not traffic_class_map:
            self._log.warning(
                "No traffic class to overlay name mapping available; shaper metrics will be emitted without "
                "the overlay_name tag"
            )
        for row in self.shaper:
            row.record(store, base_tags, traffic_class_map, self._log)

    def _record_appperf_stats(self, store: MetricsStore, base_tags: list[str]) -> None:
        for row in self.appperf:
            row.record(store, base_tags)

    def _record_dscp_stats(self, store: MetricsStore, base_tags: list[str]) -> None:
        for dscp in self.dscp:
            dscp.record(store, base_tags)
        for peak in self.dscp_peaks:
            peak.record(store, base_tags)
