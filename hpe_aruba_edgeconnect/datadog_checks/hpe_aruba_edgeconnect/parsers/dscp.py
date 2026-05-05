# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from io import StringIO

from datadog_checks.hpe_aruba_edgeconnect.constants import MINUTE_STATS_INTERVAL
from datadog_checks.hpe_aruba_edgeconnect.metrics_store import AggType, MetricsStore


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
    def parse(cls, content: str) -> Iterator[DscpStats]:
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
    def parse(cls, content: str) -> Iterator[DscpPeakStats]:
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            if row.get('traftype', '').strip() == 'all traffic':
                continue
            yield cls(row)
