# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator

from prometheus_client.samples import Sample

_AGGREGABLE_TYPES = frozenset(('gauge', 'counter'))


def should_aggregate(exclude_labels: set[str]) -> bool:
    return bool(exclude_labels)


def aggregate_sample_data(
    sample_data: Iterator[tuple[Sample, list[str], str]],
    metric_type: str,
) -> Iterator[tuple[Sample, list[str], str]]:
    if metric_type not in _AGGREGABLE_TYPES:
        yield from sample_data
        return

    groups: dict[tuple[tuple[str, ...], str], list] = {}

    for sample, tags, hostname in sample_data:
        key = _grouping_key(tags, hostname)
        entry = groups.get(key)
        if entry is None:
            groups[key] = [sample.value, sample, tags, hostname]
        else:
            entry[0] += sample.value

    for summed_value, original_sample, tags, hostname in groups.values():
        yield original_sample._replace(value=summed_value), tags, hostname


def _grouping_key(tags: list[str], hostname: str) -> tuple[tuple[str, ...], str]:
    return (tuple(sorted(tags)), hostname)
