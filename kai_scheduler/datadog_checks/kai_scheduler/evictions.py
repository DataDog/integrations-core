# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
from collections.abc import Iterable

from cachetools import LRUCache

from datadog_checks.base import AgentCheck

EVICTED_PODS_METRIC = 'kai_pod_group_evicted_pods'
EVICTED_PODS_NAME = 'evicted_pods.count'
GROUP_LABELS = frozenset({'namespace', 'nodepool', 'action'})
CACHE_SIZE = 10_000


class EvictedPodsTransformer:
    """Submit the pods evicted since the previous scrape, summed by namespace, node pool, and action.

    KAI counts evictions per pod group and never deletes those series, so they grow with every pod group ever evicted.
    Summing the raw counters would go backwards whenever a series disappears, so the increase of each series since the
    previous scrape is summed instead. Previous values are kept in a bounded LRU cache.
    """

    def __init__(self, check: AgentCheck, rename_labels: dict[str, str]):
        self.check = check
        self.rename_labels = rename_labels
        self.previous_values: LRUCache[tuple, float] = LRUCache(maxsize=CACHE_SIZE)
        self.previous_scrape_fit = True

    def __call__(self, metric, sample_data: Iterable, runtime_data: dict) -> None:
        samples = list(sample_data)
        fits = len(samples) <= self.previous_values.maxsize
        if not fits:
            self.check.log.warning(
                'Tracking %d pod group eviction series, more than the cache size of %d. '
                'Evictions of pod groups that are not cached are not reported.',
                len(samples),
                self.previous_values.maxsize,
            )
        # A series missing from the cache is new, and its whole value an increase, only if the previous scrape
        # succeeded and no series was evicted from the cache since. Otherwise it may be an old series.
        count_new_series = runtime_data['flush_first_value'] and fits and self.previous_scrape_fit
        self.previous_scrape_fit = fits

        increases: defaultdict[tuple[str, tuple[str, ...]], float] = defaultdict(float)
        for sample, tags, hostname in samples:
            key = tuple(sorted(sample.labels.items()))
            previous = self.previous_values.get(key)
            self.previous_values[key] = sample.value

            if previous is None:
                increase = sample.value if count_new_series else 0
            elif sample.value < previous:
                # The scheduler restarted and the counter started again from zero.
                increase = sample.value
            else:
                increase = sample.value - previous
            increases[(hostname, self.group_tags(sample.labels, tags))] += increase

        for (hostname, tags), increase in increases.items():
            self.check.count(EVICTED_PODS_NAME, increase, tags=list(tags), hostname=hostname)

    def group_tags(self, labels: dict[str, str], tags: list[str]) -> tuple[str, ...]:
        dropped = tuple(f'{self.rename_labels.get(name, name)}:' for name in labels if name not in GROUP_LABELS)
        return tuple(sorted(tag for tag in tags if not tag.startswith(dropped)))
