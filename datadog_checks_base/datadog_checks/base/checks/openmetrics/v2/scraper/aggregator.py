# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Iterator

from prometheus_client.samples import Sample

logger = logging.getLogger(__name__)

# Metric types whose colliding samples can be combined by summation after a
# label is excluded.
AGGREGABLE_TYPES = frozenset(('gauge', 'counter'))

# Metric types left untouched by summation. Summary quantiles are not additive,
# so they cannot be merged across a collapsed dimension; histogram buckets are
# additive in principle, but correct bucket/_sum/_count merging is not
# implemented. When aggregation is active these types skip label exclusion
# entirely so each source series stays a distinct context.
NON_SUMMABLE_SUBMETRIC_TYPES = frozenset(('histogram', 'summary'))


def aggregate_sample_data(
    sample_data: Iterator[tuple[Sample, list[str], str]],
    metric_type: str,
) -> Iterator[tuple[Sample, list[str], str]]:
    """Sum gauge/counter samples whose tags collide after label exclusion; pass other types through."""
    if metric_type not in AGGREGABLE_TYPES:
        yield from sample_data
        return

    # Buffers one entry per surviving context; memory scales with the number of
    # post-exclusion contexts, not the raw sample count.
    groups: dict[tuple[str, tuple[str, ...], str], list] = {}

    for sample, tags, hostname in sample_data:
        key = _grouping_key(sample.name, tags, hostname)
        entry = groups.get(key)
        if entry is None:
            groups[key] = [sample.value, sample, tags, hostname]
        else:
            entry[0] += sample.value

    for summed_value, original_sample, tags, hostname in groups.values():
        yield original_sample._replace(value=summed_value), tags, hostname


def _grouping_key(sample_name: str, tags: list[str], hostname: str) -> tuple[str, tuple[str, ...], str]:
    # `sample_name` keeps a counter's `_total` and `_created` samples in separate
    # groups when both reach this function (OpenMetrics parser), so summation
    # cannot fold a creation timestamp into the counter value.
    return (sample_name, tuple(sorted(tags)), hostname)
