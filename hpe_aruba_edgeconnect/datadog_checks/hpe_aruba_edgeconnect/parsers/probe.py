# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from datadog_checks.hpe_aruba_edgeconnect.constants import (
    PROBE_COL_ADMIN_UP,
    PROBE_COL_AVG_JITTER,
    PROBE_COL_AVG_LATENCY,
    PROBE_COL_AVG_LOSS,
    PROBE_COL_OPER_UP,
    PROBE_COL_TUNNEL_ALIAS,
)
from datadog_checks.hpe_aruba_edgeconnect.metrics_store import AggType, MetricsStore


@dataclass(init=False, slots=True)
class ProbeStats:
    tunnel_alias: str
    avg_latency: float
    avg_loss: float
    avg_jitter: float
    admin_up: float
    oper_up: float

    def __init__(self, cols: list[str]) -> None:
        self.tunnel_alias = cols[PROBE_COL_TUNNEL_ALIAS]
        self.avg_latency = float(cols[PROBE_COL_AVG_LATENCY])
        self.avg_loss = float(cols[PROBE_COL_AVG_LOSS])
        self.avg_jitter = float(cols[PROBE_COL_AVG_JITTER])
        self.admin_up = float(cols[PROBE_COL_ADMIN_UP])
        self.oper_up = float(cols[PROBE_COL_OPER_UP])

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        tags = base_tags + [f'probe_target:{self.tunnel_alias}']
        store.record('circuit.sla.latency', self.avg_latency, tags, AggType.AVG)
        store.record('circuit.sla.loss', self.avg_loss, tags, AggType.AVG)
        store.record('circuit.sla.jitter', self.avg_jitter, tags, AggType.AVG)
        store.record('nexthop.status', self.admin_up, tags + ['status_type:admin'], AggType.LAST)
        store.record('nexthop.status', self.oper_up, tags + ['status_type:oper'], AggType.LAST)

    @classmethod
    def parse(cls, content: str) -> Iterator[ProbeStats]:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            yield cls(line.split(','))
