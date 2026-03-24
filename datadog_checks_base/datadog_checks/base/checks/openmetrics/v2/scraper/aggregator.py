# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Iterator

from prometheus_client.samples import Sample

logger = logging.getLogger(__name__)

# Metric types where pre-aggregation is meaningful. Histograms and summaries
# have sub-metric structure (buckets, quantiles) that makes label-collision
# aggregation ambiguous, so they are left unchanged.
_AGGREGABLE_TYPES = frozenset(('gauge', 'counter'))


def should_aggregate(exclude_labels: set[str]) -> bool:
    return bool(exclude_labels)


# Pre-aggregate samples whose tags collide after label exclusion.
# Only aggregates gauge and counter. Histogram and summary samples pass
# through unchanged because their sub-metric structure makes aggregation ambiguous.
def aggregate_sample_data(
    sample_data: Iterator[tuple[Sample, list[str], str]],
    metric_type: str,
) -> Iterator[tuple[Sample, list[str], str]]:
    if metric_type not in _AGGREGABLE_TYPES:
        yield from sample_data
        return

    groups: dict[tuple, list] = {}

    for sample, tags, hostname in sample_data:
        key = _grouping_key(tags, hostname)
        entry = groups.get(key)
        if entry is None:
            groups[key] = [sample.value, sample, tags, hostname]
        else:
            entry[0] += sample.value

    for summed_value, original_sample, tags, hostname in groups.values():
        yield original_sample._replace(value=summed_value), tags, hostname


def _grouping_key(tags: list[str], hostname: str) -> tuple:
    return (tuple(sorted(tags)), hostname)
