# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck


class AggType(Enum):
    SUM = 'sum'
    AVG = 'avg'
    MAX = 'max'
    MIN = 'min'
    LAST = 'last'


class MetricsStore:
    """Accumulates per-interval metric samples and flushes aggregated values."""

    def __init__(self) -> None:
        self._metrics: dict[tuple[str, tuple[str, ...]], tuple[AggType, list[float]]] = {}

    def record(self, name: str, value: float, tags: list[str], agg_type: AggType) -> None:
        key = (name, tuple(sorted(tags)))
        entry = self._metrics.get(key)
        if entry is None:
            self._metrics[key] = (agg_type, [value])
        else:
            entry[1].append(value)

    def flush(self, check: AgentCheck) -> None:
        for (name, tags), (agg_type, values) in self._metrics.items():
            try:
                check.gauge(name, _aggregate(agg_type, values), tags=list(tags))
            except Exception as e:
                check.log.error("Error flushing metric %s with tags %s: %s", name, tags, e)
                continue


def _aggregate(agg_type: AggType, values: list[float]) -> float:
    if agg_type is AggType.SUM:
        return sum(values)
    if agg_type is AggType.AVG:
        return sum(values) / len(values)
    if agg_type is AggType.MAX:
        return max(values)
    if agg_type is AggType.MIN:
        return min(values)
    if agg_type is AggType.LAST:
        return values[-1]
    raise ValueError("Invalid aggregation type: %s", agg_type)
