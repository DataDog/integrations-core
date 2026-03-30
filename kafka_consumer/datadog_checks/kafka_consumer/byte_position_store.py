# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import bisect
import json


class PartitionByteStore:
    """Tracks known (offset, byte_position) points for a single partition.

    Uses leveled thinning: level 0 holds the finest-grained (most recent) points.
    When a level overflows, the two oldest points are removed and one is promoted
    to the next level, halving resolution at each tier.
    """

    def __init__(self, max_points_per_level: int = 60, num_levels: int = 10):
        self.max_points = max_points_per_level
        self.num_levels = num_levels
        # Each level is a sorted list of (offset, byte_position)
        self.levels: list[list[tuple[int, int]]] = [[] for _ in range(num_levels)]

    def add(self, offset: int, byte_position: int):
        _insert_sorted(self.levels[0], offset, byte_position)
        self._thin()

    def prune_below(self, min_offset: int):
        for i in range(self.num_levels):
            idx = bisect.bisect_left(self.levels[i], (min_offset,))
            self.levels[i] = self.levels[i][idx:]

    def query(self, offset: int) -> int | None:
        all_points = _merge_sorted_levels(self.levels)
        return _interpolate(all_points, offset)

    def _thin(self):
        for i in range(self.num_levels - 1):
            while len(self.levels[i]) > self.max_points:
                older = self.levels[i].pop(0)
                self.levels[i].pop(0)  # discard the second-oldest
                _insert_sorted(self.levels[i + 1], older[0], older[1])
        # Last level: just drop excess
        while len(self.levels[-1]) > self.max_points:
            self.levels[-1].pop(0)

    @property
    def total_points(self) -> int:
        return sum(len(level) for level in self.levels)


def _insert_sorted(level: list[tuple[int, int]], offset: int, byte_position: int):
    idx = bisect.bisect_left(level, (offset,))
    if idx < len(level) and level[idx][0] == offset:
        level[idx] = (offset, byte_position)
    else:
        level.insert(idx, (offset, byte_position))


def _merge_sorted_levels(levels: list[list[tuple[int, int]]]) -> list[tuple[int, int]]:
    merged: dict[int, int] = {}
    for level in levels:
        for offset, bp in level:
            if offset not in merged:
                merged[offset] = bp
    return sorted(merged.items())


def _interpolate(points: list[tuple[int, int]], offset: int) -> int | None:
    if not points:
        return None

    idx = bisect.bisect_left(points, (offset,))

    if idx < len(points) and points[idx][0] == offset:
        return points[idx][1]

    if idx == 0 or idx >= len(points):
        return None

    o1, b1 = points[idx - 1]
    o2, b2 = points[idx]
    t = (offset - o1) / (o2 - o1)
    return int(b1 + t * (b2 - b1))


class BytePositionStore:
    """Manages byte position tracking across all topic-partitions.

    Each check run provides (low_offset, high_offset, size_bytes) per partition.
    The store maintains cumulative byte positions B(offset) such that:
        B(high) - B(low) = size_bytes
    These can then be used to estimate the byte size of any sub-range,
    e.g. bytes(committed_offset, high_watermark) for consumer lag in bytes.
    """

    PERSISTENT_CACHE_KEY = "byte_position_store"

    def __init__(self, max_points_per_level: int = 60, num_levels: int = 10):
        self.max_points_per_level = max_points_per_level
        self.num_levels = num_levels
        self._stores: dict[tuple[str, int], PartitionByteStore] = {}

    def _get_or_create(self, topic: str, partition: int) -> PartitionByteStore:
        key = (topic, partition)
        if key not in self._stores:
            self._stores[key] = PartitionByteStore(self.max_points_per_level, self.num_levels)
        return self._stores[key]

    def update(self, topic: str, partition: int, low_offset: int, high_offset: int, size_bytes: int):
        store = self._get_or_create(topic, partition)

        b_low = store.query(low_offset)
        if b_low is None:
            b_low = 0
            store.add(low_offset, b_low)

        store.add(high_offset, b_low + size_bytes)
        store.prune_below(low_offset)

    def estimate_bytes(self, topic: str, partition: int, from_offset: int, to_offset: int) -> int | None:
        key = (topic, partition)
        if key not in self._stores:
            return None
        store = self._stores[key]
        b_from = store.query(from_offset)
        b_to = store.query(to_offset)
        if b_from is None or b_to is None:
            return None
        return b_to - b_from

    def to_json(self) -> str:
        data = {}
        for (topic, partition), store in self._stores.items():
            # Use JSON array as key to handle topics with underscores
            key = json.dumps([topic, partition])
            data[key] = [level[:] for level in store.levels]
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str, max_points_per_level: int = 60, num_levels: int = 10) -> BytePositionStore:
        instance = cls(max_points_per_level, num_levels)
        if not json_str:
            return instance
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return instance
        for key, levels_data in data.items():
            topic, partition = json.loads(key)
            store = instance._get_or_create(topic, int(partition))
            for i, level_data in enumerate(levels_data):
                if i < num_levels:
                    store.levels[i] = [(int(o), int(b)) for o, b in level_data]
        return instance
