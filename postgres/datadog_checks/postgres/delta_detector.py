# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PgssKey = tuple[int, int, int]  # (queryid, dbid, userid)


@dataclass
class DeltaResult:
    derivative_rows: list[dict]
    """Full pg_stat_statements row keys that changed and need obfuscation resolution."""
    changed_pgss_keys: set[PgssKey]
    """Keys that disappeared from pgss since the last snapshot; drop from obfuscation cache."""
    vanished_pgss_keys: set[PgssKey]


class DeltaDetector:
    """Diffs consecutive pgss snapshots to produce per-key derivative rows for changed statements only."""

    def __init__(self, metric_columns: frozenset[str], execution_indicators: frozenset[str] | None = None):
        self._metric_columns = metric_columns
        self._execution_indicators = execution_indicators or frozenset()
        self._previous: dict[PgssKey, dict] = {}

    def reset(self):
        self._previous.clear()

    def compute(self, rows: list[dict]) -> DeltaResult:
        """Diff *rows* against the previous snapshot."""
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
        changed_pgss_keys: set[PgssKey] = set()

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
            changed_pgss_keys.add(key)

        vanished_pgss_keys = set(self._previous.keys()) - set(current.keys())

        logger.debug(
            "delta: snapshot=%d prev=%d derivative=%d changed=%d vanished=%d",
            len(current),
            len(self._previous),
            len(derivative_rows),
            len(changed_pgss_keys),
            len(vanished_pgss_keys),
        )

        self._update_cache(current)

        return DeltaResult(
            derivative_rows=derivative_rows,
            changed_pgss_keys=changed_pgss_keys,
            vanished_pgss_keys=vanished_pgss_keys,
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
