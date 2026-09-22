# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The default batching strategy."""

from __future__ import annotations

from itertools import batched, chain
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.batching.exceptions import PlanningError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import BatchJob


def default_strategy(jobs: Sequence[BatchJob], *, config: BatchingConfig) -> list[list[BatchJob]]:
    """Pack jobs into batches, keeping each integration atomic unless it exceeds capacity.

    An integration too big for one batch raises `PlanningError` unless
    `allow_integration_splitting` is set, in which case it spills across batches.
    """
    capacity = config.max_jobs_per_batch
    batches: list[list[BatchJob]] = []
    current: list[BatchJob] = []

    for group in _group_by_integration(list(jobs)):
        if len(group) > capacity:
            if not config.allow_integration_splitting:
                raise PlanningError(
                    f"Integration {group[0].target!r} needs {len(group)} jobs, exceeding the batch "
                    f"capacity of {capacity}; enable allow_integration_splitting to span multiple batches."
                )
            # Spill across full batches, starting from the current remainder so no capacity is
            # wasted. The last chunk is short by design and stays open for following integrations.
            *full, current = map(list, batched(chain(current, group), capacity, strict=False))
            batches.extend(full)
        elif len(current) + len(group) <= capacity:
            current.extend(group)
        else:
            # Fits a batch but not this one's remainder, so start a fresh batch. `current` is
            # non-empty here, since an empty one would have matched the branch above.
            batches.append(current)
            current = list(group)

    if current:
        batches.append(current)
    return batches


def _group_by_integration(jobs: list[BatchJob]) -> list[list[BatchJob]]:
    """Group jobs by integration (`target`), preserving first-appearance order."""
    groups: dict[str, list[BatchJob]] = {}
    for job in jobs:
        groups.setdefault(job.target, []).append(job)
    return list(groups.values())
