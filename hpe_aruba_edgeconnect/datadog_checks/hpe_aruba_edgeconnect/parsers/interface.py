# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING

from datadog_checks.hpe_aruba_edgeconnect.constants import (
    MINUTE_STATS_INTERVAL,
    NDM_INTERFACE_RESOURCE_TAG,
    TUNNEL_TYPE_INTERNET_BREAKOUT,
)
from datadog_checks.hpe_aruba_edgeconnect.metrics_store import AggType, MetricsStore

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


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
    def parse(cls, content: str, logger: CheckLoggingAdapter) -> Iterator[InterfaceStats]:
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
    def parse(cls, content: str, logger: CheckLoggingAdapter) -> Iterator[InterfacePeakStats]:
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
    def parse(cls, content: str) -> Iterator[InterfaceOverlayStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if int(row.get('tuntype', '0')) != TUNNEL_TYPE_INTERNET_BREAKOUT:
                continue
            yield cls(row)
