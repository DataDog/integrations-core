# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from collections import OrderedDict
from typing import Any


class QueryMetrics:
    """Difference cached statement counters before aggregating normalized queries.

    Missing counters retain their baselines for up to an hour, within a bounded LRU
    cache. An unknown or expired counter only establishes a baseline: its lifetime
    total cannot safely be attributed to this collection interval.
    """

    def __init__(self, max_size: int = 20000, retention: float = 3600):
        self._max_size = max_size
        self._retention = retention
        self._previous: OrderedDict[tuple, tuple[float, dict[str, Any]]] = OrderedDict()

    def compute_deltas(self, rows: list[dict[str, Any]], metrics: list[str]) -> list[dict[str, Any]]:
        now = time.monotonic()
        while self._previous:
            _, (seen, _) = next(iter(self._previous.items()))
            if now - seen < self._retention:
                break
            self._previous.popitem(last=False)

        result = []
        for row in rows:
            # A plan hash describes a shape, not a counter lifetime. Offsets select
            # the statement within the handle; generation/time distinguish recompiles.
            key = (
                row.get('dbid'),
                row.get('database_name'),
                row['plan_handle'],
                row['statement_start_offset'],
                row['statement_end_offset'],
                row['plan_generation_num'],
                row['creation_time'],
            )
            previous = self._previous.get(key)
            if previous is not None and all(m in previous[1] for m in metrics):
                before = previous[1]
                deltas = {m: row[m] - before[m] for m in metrics}
                # A decrease in any counter invalidates the entire observation.
                if deltas and all(v >= 0 for v in deltas.values()) and any(v > 0 for v in deltas.values()):
                    result.append({**row, **deltas})

            self._previous[key] = (now, {m: row[m] for m in metrics if m in row})
            self._previous.move_to_end(key)

        # Evict only after refreshing every observed counter, so collection order
        # cannot evict an active baseline before it is read.
        while len(self._previous) > self._max_size:
            self._previous.popitem(last=False)
        return result
