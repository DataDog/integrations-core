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
from typing import TYPE_CHECKING, ClassVar, Protocol

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
    is_sdwan: bool
    bytes_wan_tx: float
    bytes_wan_rx: float
    bytes_lan_tx: float
    bytes_lan_rx: float
    pkts_wan_tx: float
    pkts_wan_rx: float
    pkts_lan_tx: float
    pkts_lan_rx: float
    latency: float
    latency_min: float
    loss_prefec: float
    loss_postfec: float

    def __init__(self, cols: list[str]) -> None:
        self.tunnel_id = cols[TUNNEL_V2_COL_TUNNEL_ID]
        self.tunnel_alias = cols[TUNNEL_V2_COL_ALIAS]
        self.overlay_id = cols[TUNNEL_V2_COL_OVERLAY_ID]
        self.is_sdwan = cols[TUNNEL_V2_COL_IS_SDWAN] == '1'
        self.bytes_wan_tx = float(cols[TUNNEL_V2_COL_BYTES_WAN_TX])
        self.bytes_wan_rx = float(cols[TUNNEL_V2_COL_BYTES_WAN_RX])
        self.bytes_lan_tx = float(cols[TUNNEL_V2_COL_BYTES_LAN_TX])
        self.bytes_lan_rx = float(cols[TUNNEL_V2_COL_BYTES_LAN_RX])
        self.pkts_wan_tx = float(cols[TUNNEL_V2_COL_PKTS_WAN_TX])
        self.pkts_wan_rx = float(cols[TUNNEL_V2_COL_PKTS_WAN_RX])
        self.pkts_lan_tx = float(cols[TUNNEL_V2_COL_PKTS_LAN_TX])
        self.pkts_lan_rx = float(cols[TUNNEL_V2_COL_PKTS_LAN_RX])
        self.latency = float(cols[TUNNEL_V2_COL_LATENCY_AVG]) / 100
        self.latency_min = float(cols[TUNNEL_V2_COL_LATENCY_MIN]) / 100
        self.loss_prefec = float(cols[TUNNEL_V2_COL_LOSS_PCT_PREFEC]) / 100
        self.loss_postfec = float(cols[TUNNEL_V2_COL_LOSS_PCT_POSTFEC]) / 100

    def record(self, store: MetricsStore, base_tags: list[str]) -> list[str]:
        """Records tunnel metrics and returns the extra tags for cross-referencing."""
        extra_tags = [
            f'tunnel_id:{self.tunnel_id}',
            f'overlay_id:{self.overlay_id}',
            f'is_sdwan:{self.is_sdwan}',
        ]
        base_tunnel_tags = base_tags + [f'tunnel_name:{self.tunnel_alias}'] + extra_tags
        for side, bytes_tx, bytes_rx, pkts_tx, pkts_rx in [
            ('wan', self.bytes_wan_tx, self.bytes_wan_rx, self.pkts_wan_tx, self.pkts_wan_rx),
            ('lan', self.bytes_lan_tx, self.bytes_lan_rx, self.pkts_lan_tx, self.pkts_lan_rx),
        ]:
            tags = base_tunnel_tags + [f'side:{side}']
            store.record('tunnel.throughput.tx.bytes.count', bytes_tx, tags, AggType.SUM)
            store.record('tunnel.throughput.rx.bytes.count', bytes_rx, tags, AggType.SUM)
            store.record('tunnel.throughput.tx.bytes.rate', bytes_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
            store.record('tunnel.throughput.rx.bytes.rate', bytes_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
            store.record('tunnel.throughput.tx.packets.count', pkts_tx, tags, AggType.SUM)
            store.record('tunnel.throughput.rx.packets.count', pkts_rx, tags, AggType.SUM)
            store.record('tunnel.throughput.tx.packets.rate', pkts_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
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
            yield cls(line.split(','))


@dataclass(init=False, slots=True)
class TunnelPeakStats:
    tunname: str
    peak_bytes_wan_tx: float
    peak_bytes_wan_rx: float
    peak_bytes_lan_tx: float | None
    peak_bytes_lan_rx: float | None
    peak_pkts_wan_tx: float | None
    peak_pkts_wan_rx: float | None
    peak_pkts_lan_tx: float | None
    peak_pkts_lan_rx: float | None
    peak_latency: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.tunname = row['tunname'].strip()
        self.peak_bytes_wan_tx = float(row['bytes_wtx']) if 'bytes_wtx' in row else None
        self.peak_bytes_wan_rx = float(row['bytes_wrx']) if 'bytes_wrx' in row else None
        self.peak_bytes_lan_tx = float(row['bytes_ltx']) if 'bytes_ltx' in row else None
        self.peak_bytes_lan_rx = float(row['bytes_lrx']) if 'bytes_lrx' in row else None
        self.peak_pkts_wan_tx = float(row['pkts_wtx']) if 'pkts_wtx' in row else None
        self.peak_pkts_wan_rx = float(row['pkts_wrx']) if 'pkts_wrx' in row else None
        self.peak_pkts_lan_tx = float(row['pkts_ltx']) if 'pkts_ltx' in row else None
        self.peak_pkts_lan_rx = float(row['pkts_lrx']) if 'pkts_lrx' in row else None
        self.peak_latency = float(row['latency_s']) / 100 if 'latency_s' in row else None

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
            yield cls(row)


@dataclass(init=False, slots=True)
class JitterStats:
    tunnel: str
    jitter: float
    peak_jitter: float

    def __init__(self, row: dict[str, str]) -> None:
        self.tunnel = row['tunnel'].strip()
        self.jitter = float(row[' jitter'])
        self.peak_jitter = float(row[' peak_jitter'])

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
    mos_postfec: float
    mos_prefec: float
    min_mos_postfec: float | None
    min_mos_prefec: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.tunnel = row['tunnel'].strip()
        self.mos_postfec = float(row[' mos_postfec'])
        self.mos_prefec = float(row[' mos_prefec'])
        self.min_mos_postfec = float(row[' min_mos_postfec']) if ' min_mos_postfec' in row else None
        self.min_mos_prefec = float(row[' min_mos_prefec']) if ' min_mos_prefec' in row else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        store.record('tunnel.qoe.mos', self.mos_postfec, base_tags + ['fec:post'], AggType.AVG)
        store.record('tunnel.qoe.mos', self.mos_prefec, base_tags + ['fec:pre'], AggType.AVG)
        if self.min_mos_postfec is not None:
            store.record('tunnel.qoe.mos.min', self.min_mos_postfec, base_tags + ['fec:post'], AggType.MIN)
        if self.min_mos_prefec is not None:
            store.record('tunnel.qoe.mos.min', self.min_mos_prefec, base_tags + ['fec:pre'], AggType.MIN)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[MosStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            yield cls(row)


@dataclass(init=False, slots=True)
class TunnelAvailability:
    alias: str
    seconds_down: float
    color: str
    peer: str | None

    def __init__(self, cols: list[str]) -> None:
        self.alias = cols[TUNNEL_AVAIL_COL_ALIAS]
        self.seconds_down = float(cols[TUNNEL_AVAIL_COL_SECONDS_DOWN])
        self.color = cols[TUNNEL_AVAIL_COL_COLOR]
        peer, _ = parse_tunnel_alias(self.alias)
        self.peer = peer or None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        tags = base_tags + [
            f'tunnel_name:{self.alias}',
            f'tunnel_color:{self.color}',
        ]
        if self.peer is not None:
            tags.append(f'peer:{self.peer}')
        store.record('tunnel.status', self.seconds_down, tags, AggType.SUM)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[TunnelAvailability]:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            yield cls(line.split(','))


@dataclass(init=False, slots=True)
class InterfaceStats:
    ifname: str
    bytes_tx: float
    bytes_rx: float
    fwdrops_bytes_tx: float
    fwdrops_bytes_rx: float
    fwdrops_pkts_tx: float
    fwdrops_pkts_rx: float
    max_bw_tx: float
    max_bw_rx: float
    traftype: str
    _log: CheckLoggingAdapter

    def __init__(self, row: dict[str, str], logger: CheckLoggingAdapter) -> None:
        self.ifname = row['ifname'].strip()
        self.bytes_tx = float(row['bytes_tx'])
        self.bytes_rx = float(row['bytes_rx'])
        self.fwdrops_bytes_tx = float(row['fwdrops_bytes_tx'])
        self.fwdrops_bytes_rx = float(row['fwdrops_bytes_rx'])
        self.fwdrops_pkts_tx = float(row['fwdrops_pkts_tx'])
        self.fwdrops_pkts_rx = float(row['fwdrops_pkts_rx'])
        self.max_bw_tx = float(row['max_bw_tx'])
        self.max_bw_rx = float(row['max_bw_rx'])
        self.traftype = row.get('traftype', '').strip()
        self._log = logger

    def record(self, store: MetricsStore, base_tags: list[str], device_id: str) -> None:
        tags = base_tags + [
            f'interface_name:{self.ifname}',
            f'traffic_type:{self.traftype}',
            f'{NDM_INTERFACE_RESOURCE_TAG}:{device_id}',
        ]
        bw_tx = self.bytes_tx / MINUTE_STATS_INTERVAL
        bw_rx = self.bytes_rx / MINUTE_STATS_INTERVAL
        store.record('interface.bandwidth.tx.count', self.bytes_tx, tags, AggType.SUM)
        store.record('interface.bandwidth.rx.count', self.bytes_rx, tags, AggType.SUM)
        store.record('interface.bandwidth.tx.rate', bw_tx, tags, AggType.AVG)
        store.record('interface.bandwidth.rx.rate', bw_rx, tags, AggType.AVG)
        store.record('interface.drops.bytes.tx.count', self.fwdrops_bytes_tx, tags, AggType.SUM)
        store.record('interface.drops.bytes.rx.count', self.fwdrops_bytes_rx, tags, AggType.SUM)
        store.record('interface.drops.packets.tx.count', self.fwdrops_pkts_tx, tags, AggType.SUM)
        store.record('interface.drops.packets.rx.count', self.fwdrops_pkts_rx, tags, AggType.SUM)
        store.record('interface.drops.bytes.tx.rate', self.fwdrops_bytes_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
        store.record('interface.drops.bytes.rx.rate', self.fwdrops_bytes_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
        store.record('interface.drops.packets.tx.rate', self.fwdrops_pkts_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
        store.record('interface.drops.packets.rx.rate', self.fwdrops_pkts_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
        if self.max_bw_tx == 0 or self.max_bw_rx == 0:
            self._log.warning(
                "Max bandwidth is not available for %s, skipping average utilization metrics", self.ifname
            )
        else:
            store.record('interface.utilization.tx.avg', bw_tx / self.max_bw_tx * 100, tags, AggType.AVG)
            store.record('interface.utilization.rx.avg', bw_rx / self.max_bw_rx * 100, tags, AggType.AVG)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[InterfaceStats]:
        if logger is None:
            raise ValueError("InterfaceStats.parse requires a logger")
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if row.get('traftype', '').strip() == 'all traffic':
                continue
            yield cls(row, logger)


@dataclass(init=False, slots=True)
class InterfacePeakStats:
    ifname: str
    peak_bytes_tx: float
    peak_bytes_rx: float
    peak_fwdrops_pkts_tx: float
    peak_fwdrops_pkts_rx: float
    peak_fwdrops_bytes_tx: float
    peak_fwdrops_bytes_rx: float
    peak_max_bw_tx: float
    peak_max_bw_rx: float
    traftype: str
    _log: CheckLoggingAdapter

    def __init__(self, row: dict[str, str], logger: CheckLoggingAdapter) -> None:
        self.ifname = row['ifname'].strip()
        self.peak_bytes_tx = float(row['bytes_tx'])
        self.peak_bytes_rx = float(row['bytes_rx'])
        self.peak_fwdrops_pkts_tx = float(row['fwdrops_pkts_tx'])
        self.peak_fwdrops_pkts_rx = float(row['fwdrops_pkts_rx'])
        self.peak_fwdrops_bytes_tx = float(row['fwdrops_bytes_tx'])
        self.peak_fwdrops_bytes_rx = float(row['fwdrops_bytes_rx'])
        self.peak_max_bw_tx = float(row['max_bw_tx'])
        self.peak_max_bw_rx = float(row['max_bw_rx'])
        self.traftype = row.get('traftype', '').strip()
        self._log = logger

    def record(self, store: MetricsStore, base_tags: list[str], device_id: str, max_bw: tuple[float, float]) -> None:
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
        peak_bw_tx = self.peak_bytes_tx / MINUTE_STATS_INTERVAL
        peak_bw_rx = self.peak_bytes_rx / MINUTE_STATS_INTERVAL
        if max_bw_tx == 0 or max_bw_rx == 0:
            self._log.warning("Max bandwidth is not available for %s, skipping peak utilization metrics", self.ifname)
        else:
            store.record('interface.utilization.tx.max', peak_bw_tx / max_bw_tx * 100, tags, AggType.MAX)
            store.record('interface.utilization.rx.max', peak_bw_rx / max_bw_rx * 100, tags, AggType.MAX)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[InterfacePeakStats]:
        if logger is None:
            raise ValueError("InterfacePeakStats.parse requires a logger")
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if row.get('traftype', '').strip() == 'all traffic':
                continue
            yield cls(row, logger)


@dataclass(init=False, slots=True)
class InterfaceOverlayStats:
    ifname: str
    bytes_tx: float
    bytes_rx: float
    max_bw_tx: float
    max_bw_rx: float

    def __init__(self, row: dict[str, str]) -> None:
        self.ifname = row['ifname'].strip()
        self.bytes_tx = float(row['bytes_tx'])
        self.bytes_rx = float(row['bytes_rx'])
        self.max_bw_tx = float(row['max_bw_tx'])
        self.max_bw_rx = float(row['max_bw_rx'])

    def record(self, store: MetricsStore, base_tags: list[str], device_id: str) -> None:
        tags = base_tags + [
            f'interface_name:{self.ifname}',
            f'{NDM_INTERFACE_RESOURCE_TAG}:{device_id}',
        ]
        store.record('tunnel.internet_breakout.bandwidth.tx.count', self.bytes_tx, tags, AggType.SUM)
        store.record('tunnel.internet_breakout.bandwidth.rx.count', self.bytes_rx, tags, AggType.SUM)
        store.record(
            'tunnel.internet_breakout.bandwidth.tx.rate', self.bytes_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG
        )
        store.record(
            'tunnel.internet_breakout.bandwidth.rx.rate', self.bytes_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG
        )
        store.record('tunnel.internet_breakout.bandwidth.tx.max', self.max_bw_tx, tags, AggType.MAX)
        store.record('tunnel.internet_breakout.bandwidth.rx.max', self.max_bw_rx, tags, AggType.MAX)

    @classmethod
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator[InterfaceOverlayStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if int(row.get('tuntype', '0')) != TUNNEL_TYPE_INTERNET_BREAKOUT:
                continue
            yield cls(row)


@dataclass(init=False, slots=True)
class DscpStats:
    dscp: str
    traftype: str
    bytes_wan_tx: float
    bytes_wan_rx: float
    bytes_lan_tx: float
    bytes_lan_rx: float

    def __init__(self, row: dict[str, str]) -> None:
        self.dscp = row['dscp'].strip()
        self.traftype = row.get('traftype', '').strip()
        self.bytes_wan_tx = float(row['bytes_wtx'])
        self.bytes_wan_rx = float(row['bytes_wrx'])
        self.bytes_lan_tx = float(row['bytes_ltx'])
        self.bytes_lan_rx = float(row['bytes_lrx'])

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        dscp_tags = base_tags + [f'dscp:{self.dscp}', f'traffic_type:{self.traftype}']
        store.record('qos.class.bandwidth.tx.count', self.bytes_wan_tx, dscp_tags + ['side:wan'], AggType.SUM)
        store.record('qos.class.bandwidth.rx.count', self.bytes_wan_rx, dscp_tags + ['side:wan'], AggType.SUM)
        store.record('qos.class.bandwidth.tx.count', self.bytes_lan_tx, dscp_tags + ['side:lan'], AggType.SUM)
        store.record('qos.class.bandwidth.rx.count', self.bytes_lan_rx, dscp_tags + ['side:lan'], AggType.SUM)
        store.record(
            'qos.class.bandwidth.tx.rate',
            self.bytes_wan_tx / MINUTE_STATS_INTERVAL,
            dscp_tags + ['side:wan'],
            AggType.AVG,
        )
        store.record(
            'qos.class.bandwidth.rx.rate',
            self.bytes_wan_rx / MINUTE_STATS_INTERVAL,
            dscp_tags + ['side:wan'],
            AggType.AVG,
        )
        store.record(
            'qos.class.bandwidth.tx.rate',
            self.bytes_lan_tx / MINUTE_STATS_INTERVAL,
            dscp_tags + ['side:lan'],
            AggType.AVG,
        )
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
    peak_bytes_wan_tx: float
    peak_bytes_wan_rx: float
    peak_bytes_lan_tx: float | None
    peak_bytes_lan_rx: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.dscp = row['dscp'].strip()
        self.traftype = row.get('traftype', '').strip()
        self.peak_bytes_wan_tx = float(row['bytes_wtx'])
        self.peak_bytes_wan_rx = float(row['bytes_wrx'])
        self.peak_bytes_lan_tx = float(row['bytes_ltx']) if 'bytes_ltx' in row else None
        self.peak_bytes_lan_rx = float(row['bytes_lrx']) if 'bytes_lrx' in row else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        dscp_tags = base_tags + [f'dscp:{self.dscp}', f'traffic_type:{self.traftype}']
        wan_tags = dscp_tags + ['side:wan']
        store.record('qos.class.bandwidth.tx.max', self.peak_bytes_wan_tx, wan_tags, AggType.MAX)
        store.record('qos.class.bandwidth.rx.max', self.peak_bytes_wan_rx, wan_tags, AggType.MAX)
        if self.peak_bytes_lan_tx is not None:
            lan_tags = dscp_tags + ['side:lan']
            store.record('qos.class.bandwidth.tx.max', self.peak_bytes_lan_tx, lan_tags, AggType.MAX)
        if self.peak_bytes_lan_rx is not None:
            lan_tags = dscp_tags + ['side:lan']
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
    avg_latency: float
    avg_loss: float
    avg_jitter: float
    admin_up: float
    oper_up: float

    def __init__(self, cols: list[str]) -> None:
        self.probe_name = cols[PROBE_COL_PROBE_NAME]
        self.avg_latency = float(cols[PROBE_COL_AVG_LATENCY])
        self.avg_loss = float(cols[PROBE_COL_AVG_LOSS])
        self.avg_jitter = float(cols[PROBE_COL_AVG_JITTER])
        self.admin_up = float(cols[PROBE_COL_ADMIN_UP])
        self.oper_up = float(cols[PROBE_COL_OPER_UP])

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


@dataclass(init=False, slots=True)
class ShaperStats:
    traffic_class: str
    direction: str
    qos_drops: float
    other_drops: float
    total_shaped_packets: float | None

    def __init__(self, row: dict[str, str]) -> None:
        self.traffic_class = row['traffic_class']
        self.direction = row['direction']
        self.qos_drops = float(row['qos_drops'])
        self.other_drops = float(row['other_drops'])
        self.total_shaped_packets = float(row['shaped_packets']) if 'shaped_packets' in row else None

    def record(
        self,
        store: MetricsStore,
        base_tags: list[str],
        traffic_class_map: dict[str, str] | None = None,
        logger: CheckLoggingAdapter | None = None,
    ) -> None:
        traffic_class_map = traffic_class_map or {}
        if self.traffic_class in traffic_class_map:
            overlay_name = traffic_class_map[self.traffic_class]
        else:
            overlay_name = self.traffic_class
            if logger is not None:
                logger.warning(
                    "No overlay name mapping found for traffic class %s; falling back to raw id", self.traffic_class
                )
        tags = base_tags + [
            f'overlay_name:{overlay_name}',
            f'direction:{self.direction}',
        ]
        store.record('qos.class.drops', self.qos_drops, tags + ['drop_type:qos'], AggType.SUM)
        store.record('qos.class.drops', self.other_drops, tags + ['drop_type:other'], AggType.SUM)
        if self.total_shaped_packets is not None and self.total_shaped_packets > 0:
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
    tunnel_name: str | None
    transport_type: str | None
    cnd_delay: float | None
    snd_delay: float | None
    app_delay: float | None

    def __init__(self, cols: list[str]) -> None:
        self.app_name = cols[APPPERF_COL_APP_NAME]
        self.tunnel_name = cols[APPPERF_COL_TUNNEL_NAME] if len(cols) > APPPERF_COL_TUNNEL_NAME else None
        self.transport_type = cols[APPPERF_COL_TRANSPORT_TYPE] if len(cols) > APPPERF_COL_TRANSPORT_TYPE else None
        self.cnd_delay = float(cols[APPPERF_COL_CND_DELAY]) if len(cols) > APPPERF_COL_CND_DELAY else None
        self.snd_delay = float(cols[APPPERF_COL_SND_DELAY]) if len(cols) > APPPERF_COL_SND_DELAY else None
        self.app_delay = float(cols[APPPERF_COL_APP_DELAY]) if len(cols) > APPPERF_COL_APP_DELAY else None

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
    def parse(cls, content: str, logger: CheckLoggingAdapter | None = None) -> Iterator: ...


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
    ) -> None:
        self._record_interface_stats(store, base_tags, device_id)
        self._record_tunnel_stats(store, base_tags)
        self._record_tunnel_availability_stats(store, base_tags)
        self._record_internet_breakout_stats(store, base_tags, device_id)
        self._record_probe_stats(store, base_tags)
        self._record_shaper_stats(store, base_tags, traffic_class_map or {})
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

    def _record_shaper_stats(
        self, store: MetricsStore, base_tags: list[str], traffic_class_map: dict[str, str]
    ) -> None:
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
