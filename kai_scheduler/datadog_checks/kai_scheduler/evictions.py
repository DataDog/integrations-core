# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING

from datadog_checks.base import AgentCheck

if TYPE_CHECKING:
    from .check import KaiOpenMetricsScraper

EVICTED_PODS_METRIC = 'kai_pod_group_evicted_pods'
EVICTED_PODS_NAME = 'evicted_pods.count'
GROUP_LABELS = ('namespace', 'nodepool', 'action')
CACHE_SIZE = 10_000

Group = tuple[str, tuple[str, ...]]


class EvictedPodsTransformer:
    """Submit the pods evicted since the previous scrape, summed by namespace, node pool, and action.

    KAI counts evictions per pod group and never deletes those series, so they grow with every pod group ever evicted.
    Summing the raw counters would go backwards whenever a series disappears, so the increase of each series since the
    previous scrape is summed instead. The previous non-zero values are cached, and the cache is rebuilt from every
    scrape so that it never keeps series that disappeared.

    When there are more than `CACHE_SIZE` non-zero series, the increase of each group's raw sum is reported instead.
    This is exact while no series disappears, and otherwise undercounts the groups that lost series. Exact counting
    resumes once a scrape that fits has rebuilt the cache.
    """

    def __init__(self, check: AgentCheck, scraper: KaiOpenMetricsScraper):
        self.check = check
        self.scraper = scraper
        self.group_prefixes = tuple(f'{scraper.rename_labels.get(name, name)}:' for name in GROUP_LABELS)
        self.previous_values: dict[int, float] = {}
        self.cache_complete = False
        self.overflowed = False
        self.previous_group_sums: dict[Group, float] = {}

    def __call__(self, metric, sample_data: Iterable, runtime_data: dict) -> None:
        samples = list(sample_data)
        nonzero = sum(1 for sample, _, _ in samples if sample.value)
        fits = nonzero <= CACHE_SIZE
        if not fits and not self.overflowed:
            self.check.log.warning(
                'Tracking %d non-zero pod group eviction series, more than the cache size of %d. Reporting the '
                'increase of the summed counters instead, which undercounts evictions when series disappear.',
                nonzero,
                CACHE_SIZE,
            )
        self.overflowed = not fits

        exact = fits and self.cache_complete
        current_values: dict[int, float] = {}

        # Before the first successful scrape, a series or group missing from the previous state may be old.
        count_new = self.scraper.scraped_successfully
        static_tags = set(self.scraper.tags)
        increases: defaultdict[Group, float] = defaultdict(float)
        group_sums: defaultdict[Group, float] = defaultdict(float)
        for sample, tags, hostname in samples:
            # Only the group labels and the tags shared by every metric of the endpoint are kept.
            group_tags = {tag for tag in tags if tag in static_tags or tag.startswith(self.group_prefixes)}
            group = (hostname, tuple(sorted(group_tags)))
            group_sums[group] += sample.value
            if not fits:
                continue

            key = hash(tuple(sorted(sample.labels.items())))
            previous = self.previous_values.get(key)
            if sample.value:
                current_values[key] = sample.value
            if not exact:
                continue

            if previous is None:
                increase = sample.value if count_new else 0
            elif sample.value < previous:
                # The scheduler restarted and the counter started again from zero.
                increase = sample.value
            else:
                increase = sample.value - previous
            increases[group] += increase

        if not exact:
            for group, total in group_sums.items():
                previous_sum = self.previous_group_sums.get(group)
                if previous_sum is None:
                    increases[group] = total if count_new else 0
                else:
                    increases[group] = max(total - previous_sum, 0)

        self.previous_values = current_values
        self.cache_complete = fits
        self.previous_group_sums = dict(group_sums)
        for (hostname, tags), increase in increases.items():
            self.check.count(EVICTED_PODS_NAME, increase, tags=list(tags), hostname=hostname)
