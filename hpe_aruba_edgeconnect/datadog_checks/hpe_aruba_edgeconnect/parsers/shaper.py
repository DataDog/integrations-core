# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from datadog_checks.hpe_aruba_edgeconnect.metrics_store import AggType, MetricsStore

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


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
    def parse(cls, content: str) -> Iterator[ShaperStats]:
        reader = csv.DictReader(io.StringIO(content), skipinitialspace=True)
        for row in reader:
            yield cls(row)
