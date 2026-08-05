# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Callable, Hashable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeltaResult[K: Hashable]:
    derivative_rows: list[dict]
    """Rows whose counters advanced since the previous snapshot, with metric columns replaced by their deltas."""
    changed_keys: set[K]
    """Keys of the rows in ``derivative_rows``."""
    vanished_keys: set[K]
    """Keys present in the previous snapshot but absent from this one."""


class DeltaDetector[K: Hashable]:
    """Diffs consecutive snapshots of cumulative counters to produce per-key derivative rows.

    Statistics tables such as ``pg_stat_statements``, MySQL's
    ``events_statements_summary_by_digest`` and SQL Server's ``dm_exec_query_stats`` expose
    counters that only increase, so per-interval values come from diffing successive snapshots.

    Rows are identified by the ``key`` callable, which must return the same value for every row
    belonging to one cumulative counter series. Rows sharing a key within a single snapshot are
    summed before diffing.

    Only keys whose counters advanced are reported, so callers can restrict expensive per-row work
    (query text resolution, obfuscation) to statements that actually ran during the interval.
    """

    def __init__(
        self,
        metric_columns: frozenset[str] | set[str],
        key: Callable[[dict], K],
        execution_indicators: frozenset[str] | set[str] | None = None,
    ):
        self._metric_columns = frozenset(metric_columns)
        self._key = key
        # Counters that only advance when a statement executes. When set, a key whose indicators are
        # all flat is skipped without diffing the remaining columns.
        self._execution_indicators = frozenset(execution_indicators or ())
        self._previous: dict[K, dict] = {}

    def reset(self):
        self._previous.clear()

    def compute(self, rows: list[dict]) -> DeltaResult[K]:
        """Diff *rows* against the previous snapshot and remember them for the next call."""
        current = self._collapse(rows)

        derivative_rows: list[dict] = []
        changed_keys: set[K] = set()

        available_metrics: frozenset[str] | None = None
        indicator_cols: frozenset[str] | None = None

        for key, row in current.items():
            prev = self._previous.get(key)
            if prev is None:
                # First time we've seen this key; there is no baseline to subtract yet.
                continue

            if available_metrics is None:
                available_metrics = self._metric_columns & row.keys() & prev.keys()
                indicator_cols = self._execution_indicators & available_metrics

            if indicator_cols and not any(row[col] - prev[col] > 0 for col in indicator_cols):
                continue

            has_negative = False
            has_change = False
            for col in available_metrics:
                diff = row[col] - prev[col]
                if diff < 0:
                    # A counter went backwards, so the series was reset and the diff is meaningless.
                    # Drop the row; the next cycle re-baselines against it.
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
            changed_keys.add(key)

        vanished_keys = self._previous.keys() - current.keys()

        logger.debug(
            "delta: snapshot=%d prev=%d derivative=%d changed=%d vanished=%d",
            len(current),
            len(self._previous),
            len(derivative_rows),
            len(changed_keys),
            len(vanished_keys),
        )

        self._update_cache(current)

        return DeltaResult(
            derivative_rows=derivative_rows,
            changed_keys=changed_keys,
            vanished_keys=vanished_keys,
        )

    def _collapse(self, rows: list[dict]) -> dict[K, dict]:
        """Group rows by key, summing metric columns across rows that share one.

        Rows are copied rather than accumulated into, so a caller that holds on to the snapshot it
        passed in does not see its counters silently rewritten.
        """
        collapsed: dict[K, dict] = {}
        for row in rows:
            key = self._key(row)
            existing = collapsed.get(key)
            if existing is None:
                collapsed[key] = dict(row)
                continue
            for col in self._metric_columns:
                if col in row:
                    existing[col] = existing.get(col, 0) + row[col]
        return collapsed

    def _update_cache(self, current: dict[K, dict]):
        stale = self._previous.keys() - current.keys()
        for k in stale:
            del self._previous[k]

        for key, row in current.items():
            prev = self._previous.get(key)
            if prev is not None:
                # Only the metric columns are retained; everything else is re-read each cycle.
                for col in self._metric_columns:
                    if col in row:
                        prev[col] = row[col]
                    elif col in prev:
                        del prev[col]
            else:
                self._previous[key] = {col: row[col] for col in self._metric_columns if col in row}
