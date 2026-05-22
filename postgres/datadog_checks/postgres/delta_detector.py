# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PgssKey = tuple[int, int, int]  # (queryid, dbid, userid)


@dataclass
class DeltaResult:
    derivative_rows: list[dict]
    changed_queryids: set[int]
    vanished_queryids: set[int]


class DeltaDetector:
    """Computes derivative counter values from pg_stat_statements snapshots.

    Operates entirely in queryid-space using lightweight integer-only rows
    (no query text, no obfuscation). Each snapshot is diffed against the
    previous one to produce per-(queryid, dbid, userid) derivative rows for
    only the statements whose counters actually changed.
    """

    def __init__(self, metric_columns: frozenset[str], execution_indicators: frozenset[str] | None = None):
        self._metric_columns = metric_columns
        self._execution_indicators = execution_indicators or frozenset()
        self._previous: dict[PgssKey, dict] = {}

    def reset(self):
        self._previous.clear()

    def compute(self, rows: list[dict]) -> DeltaResult:
        """Diff *rows* against the previous snapshot and return a DeltaResult.

        Each element of *rows* must contain at least ``queryid``, ``dbid``,
        ``userid`` (the pgss natural key) plus the counter columns configured
        at init time.  Non-metric columns (e.g. ``datname``, ``rolname``) are
        carried through to the derivative rows unchanged.
        """
        current: dict[PgssKey, dict] = {}
        for row in rows:
            key = (row['queryid'], row['dbid'], row['userid'])
            if key in current:
                for col in self._metric_columns:
                    if col in row:
                        current[key][col] = current[key].get(col, 0) + row[col]
            else:
                current[key] = row

        derivative_rows: list[dict] = []
        changed_queryids: set[int] = set()

        available_metrics: frozenset[str] | None = None
        indicator_cols: frozenset[str] | None = None

        for key, row in current.items():
            prev = self._previous.get(key)
            if prev is None:
                continue

            if available_metrics is None:
                available_metrics = self._metric_columns & row.keys() & prev.keys()
                if self._execution_indicators:
                    indicator_cols = self._execution_indicators & available_metrics

            if indicator_cols:
                if not any(row[col] - prev[col] > 0 for col in indicator_cols):
                    continue

            has_negative = False
            has_change = False
            for col in available_metrics:
                diff = row[col] - prev[col]
                if diff < 0:
                    has_negative = True
                    break
                if diff != 0:
                    has_change = True

            if has_negative or not has_change:
                continue

            derivative = {}
            for col in row:
                if col in available_metrics:
                    derivative[col] = row[col] - prev[col]
                else:
                    derivative[col] = row[col]
            derivative_rows.append(derivative)
            changed_queryids.add(key[0])

        vanished_queryids = {k[0] for k in self._previous if k not in current}

        self._update_cache(current)

        return DeltaResult(
            derivative_rows=derivative_rows,
            changed_queryids=changed_queryids,
            vanished_queryids=vanished_queryids,
        )

    def _update_cache(self, current: dict[PgssKey, dict]):
        stale = self._previous.keys() - current.keys()
        for k in stale:
            del self._previous[k]

        for key, row in current.items():
            prev = self._previous.get(key)
            if prev is not None:
                for col in self._metric_columns:
                    if col in row:
                        prev[col] = row[col]
                    elif col in prev:
                        del prev[col]
            else:
                self._previous[key] = {col: row[col] for col in self._metric_columns if col in row}
