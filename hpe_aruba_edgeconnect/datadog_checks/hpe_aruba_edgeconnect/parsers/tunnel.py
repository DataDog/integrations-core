# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from dataclasses import dataclass
from io import StringIO

from datadog_checks.hpe_aruba_edgeconnect.constants import (
    MINUTE_STATS_INTERVAL,
    TUNNEL_AVAIL_COL_ALIAS,
    TUNNEL_AVAIL_COL_COLOR,
    TUNNEL_AVAIL_COL_SECONDS_DOWN,
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

_TUNNEL_ALIAS_RE = re.compile(r'^to_\w+_')


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
            store.record('tunnel.throughput.tx.bps.count', bytes_tx, tags, AggType.SUM)
            store.record('tunnel.throughput.rx.bps.count', bytes_rx, tags, AggType.SUM)
            store.record('tunnel.throughput.tx.bps.rate', bytes_tx * 8 / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
            store.record('tunnel.throughput.rx.bps.rate', bytes_rx * 8 / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
            store.record('tunnel.throughput.tx.pps.count', pkts_tx, tags, AggType.SUM)
            store.record('tunnel.throughput.rx.pps.count', pkts_rx, tags, AggType.SUM)
            store.record('tunnel.throughput.tx.pps.rate', pkts_tx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
            store.record('tunnel.throughput.rx.pps.rate', pkts_rx / MINUTE_STATS_INTERVAL, tags, AggType.AVG)
        store.record('tunnel.latency', self.latency, base_tunnel_tags, AggType.AVG)
        store.record('tunnel.latency.min', self.latency_min, base_tunnel_tags, AggType.MIN)
        store.record('tunnel.loss', self.loss_postfec, base_tunnel_tags + ['fec:post'], AggType.AVG)
        store.record('tunnel.loss', self.loss_prefec, base_tunnel_tags + ['fec:pre'], AggType.AVG)
        return extra_tags

    @classmethod
    def parse(cls, content: str) -> Iterator[TunnelV2Stats]:
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
        self.peak_bytes_wan_tx = float(row['bytes_wtx'])
        self.peak_bytes_wan_rx = float(row['bytes_wrx'])
        self.peak_bytes_lan_tx = float(row['bytes_ltx'])
        self.peak_bytes_lan_rx = float(row['bytes_lrx'])
        self.peak_pkts_wan_tx = float(row['pkts_wtx'])
        self.peak_pkts_wan_rx = float(row['pkts_wrx'])
        self.peak_pkts_lan_tx = float(row['pkts_ltx'])
        self.peak_pkts_lan_rx = float(row['pkts_lrx'])
        self.peak_latency = float(row['latency_s']) / 100

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
                store.record('tunnel.throughput.tx.bps.max', bytes_tx, tags, AggType.MAX)
            if bytes_rx is not None:
                store.record('tunnel.throughput.rx.bps.max', bytes_rx, tags, AggType.MAX)
            if pkts_tx is not None:
                store.record('tunnel.throughput.tx.pps.max', pkts_tx, tags, AggType.MAX)
            if pkts_rx is not None:
                store.record('tunnel.throughput.rx.pps.max', pkts_rx, tags, AggType.MAX)
        if self.peak_latency is not None:
            store.record('tunnel.latency.max', self.peak_latency, base_tunnel_tags, AggType.MAX)

    @classmethod
    def parse(cls, content: str) -> Iterator[TunnelPeakStats]:
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
    def parse(cls, content: str) -> Iterator[JitterStats]:
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
    def parse(cls, content: str) -> Iterator[MosStats]:
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
        self.peer = self.alias.split('_')[1] if _TUNNEL_ALIAS_RE.match(self.alias) else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        tags = base_tags + [
            f'tunnel_name:{self.alias}',
            f'tunnel_color:{self.color}',
        ]
        if self.peer is not None:
            tags.append(f'peer:{self.peer}')
        store.record('tunnel.status', self.seconds_down, tags, AggType.SUM)

    @classmethod
    def parse(cls, content: str) -> Iterator[TunnelAvailability]:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            yield cls(line.split(','))
