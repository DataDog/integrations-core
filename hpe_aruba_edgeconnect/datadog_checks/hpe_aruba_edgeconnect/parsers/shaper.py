# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass

from datadog_checks.hpe_aruba_edgeconnect.metrics_store import AggType, MetricsStore


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

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        tags = base_tags + [
            f'traffic_class:{self.traffic_class}',
            f'direction:{self.direction}',
        ]
        store.record('qos.class.drops', self.qos_drops, tags + ['drop_type:qos'], AggType.SUM)
        store.record('qos.class.drops', self.other_drops, tags + ['drop_type:other'], AggType.SUM)
        if self.total_shaped_packets is not None and self.total_shaped_packets > 0:
            store.record(
                'qos.class.drop.percentage', self.qos_drops / self.total_shaped_packets * 100, tags, AggType.AVG
            )

    @classmethod
    def parse(cls, content: str) -> Iterator[ShaperStats]:
        reader = csv.DictReader(io.StringIO(content), skipinitialspace=True)
        for row in reader:
            yield cls(row)
