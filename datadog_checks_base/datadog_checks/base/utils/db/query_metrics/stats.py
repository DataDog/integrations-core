# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Delta[K: Hashable]:
    derivative_rows: list[dict]
    """Rows whose counters advanced since the previous snapshot, with counter columns replaced by
    their deltas."""
    changed_keys: set[K]
    """Keys of :attr:`derivative_rows`, for resolving statement text only for what actually ran."""
    pending_baselines: dict[K, dict] = field(default_factory=dict, repr=False, compare=False)
    """Counter values of `changed_keys` held back by `QueryStats.diff(commit=False)`, installed by
    `QueryStats.commit`. Empty when the diff committed."""


class QueryStats[K: Hashable]:
    """Diffs consecutive snapshots of cumulative query statistics into per-interval rows.

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
        counter_columns: frozenset[str] | set[str],
        key: Callable[[dict], K],
        execution_indicators: frozenset[str] | set[str] | None = None,
    ):
        self._counter_columns = frozenset(counter_columns)
        self._key = key
        # Counters that only advance when a statement executes. When set, a key whose indicators are
        # all flat is skipped without diffing the remaining columns.
        self._execution_indicators = frozenset(execution_indicators or ())
        self._previous: dict[K, dict] = {}

    def reset(self):
        self._previous.clear()

    def diff(self, snapshot: list[dict], *, commit: bool = True) -> Delta[K]:
        """Diff *snapshot* against the committed baseline.

        By default *snapshot* becomes the baseline for the next call. Pass `commit=False` when work
        that follows the diff, such as fetching statement text, can fail: keys in `changed_keys` keep
        their previous baseline until the delta is passed to `commit`, so if it never is, the next
        diff reports their interval too instead of losing it. Every other key is baselined
        immediately, since it has no delta to retry: holding back a new or reset key would discard
        its counts up to the next successful collection.

        Commit before emitting the delta, and before the next diff. Emitting a delta and then not
        committing it reports that interval twice.
        """
        current = self._collapse(snapshot)

        derivative_rows: list[dict] = []
        changed_keys: set[K] = set()

        available_counters: frozenset[str] | None = None
        indicator_cols: frozenset[str] | None = None

        for key, row in current.items():
            prev = self._previous.get(key)
            if prev is None:
                # First time we've seen this key; there is no baseline to subtract yet.
                continue

            if available_counters is None:
                available_counters = self._counter_columns & row.keys() & prev.keys()
                indicator_cols = self._execution_indicators & available_counters

            if indicator_cols and not any(row[col] - prev[col] > 0 for col in indicator_cols):
                continue

            has_negative = False
            has_change = False
            for col in available_counters:
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
                if col in available_counters:
                    derivative[col] = row[col] - prev[col]
                else:
                    derivative[col] = row[col]
            derivative_rows.append(derivative)
            changed_keys.add(key)

        logger.debug(
            "diff: snapshot=%d prev=%d derivative=%d changed=%d",
            len(current),
            len(self._previous),
            len(derivative_rows),
            len(changed_keys),
        )

        if commit:
            self._remember(current)
            return Delta(derivative_rows=derivative_rows, changed_keys=changed_keys)

        pending = {key: self._counters(current[key]) for key in changed_keys}
        self._remember(current, skip=changed_keys)
        return Delta(derivative_rows=derivative_rows, changed_keys=changed_keys, pending_baselines=pending)

    def commit(self, delta: Delta[K]):
        """Install the baselines a `diff(commit=False)` held back for *delta*'s changed keys."""
        self._previous.update(delta.pending_baselines)
        delta.pending_baselines = {}

    def _collapse(self, snapshot: list[dict]) -> dict[K, dict]:
        """Group rows by key, summing counter columns across rows that share one.

        Rows are copied rather than accumulated into, so a caller that holds on to the snapshot it
        passed in does not see its counters silently rewritten.
        """
        collapsed: dict[K, dict] = {}
        for row in snapshot:
            key = self._key(row)
            existing = collapsed.get(key)
            if existing is None:
                collapsed[key] = dict(row)
                continue
            for col in self._counter_columns:
                if col in row:
                    existing[col] = existing.get(col, 0) + row[col]
        return collapsed

    def _counters(self, row: dict) -> dict:
        return {col: row[col] for col in self._counter_columns if col in row}

    def _remember(self, current: dict[K, dict], skip: set[K] | None = None):
        stale = self._previous.keys() - current.keys()
        for k in stale:
            del self._previous[k]

        for key, row in current.items():
            if skip and key in skip:
                continue
            prev = self._previous.get(key)
            if prev is not None:
                # Only the counter columns are retained; everything else is re-read each cycle.
                for col in self._counter_columns:
                    if col in row:
                        prev[col] = row[col]
                    elif col in prev:
                        del prev[col]
            else:
                self._previous[key] = self._counters(row)
