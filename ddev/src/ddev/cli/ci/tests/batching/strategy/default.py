# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The default batching strategy.

:func:`default_strategy` keeps each integration atomic whenever it fits a batch and only splits an
integration whose job count exceeds capacity, and only when the configuration permits it. This
module holds only the default algorithm; the extension contract lives in
:mod:`~ddev.cli.ci.tests.batching.strategy.types` and strategy-independent validation and message
construction live in sibling modules so new strategies can be added without touching this one.
"""

from __future__ import annotations

from itertools import batched, chain
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.batching.exceptions import PlanningError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import BatchJob


def default_strategy(
    jobs: Sequence[BatchJob],
    *,
    capacity: int,
    config: BatchingConfig,
) -> list[list[BatchJob]]:
    """Pack jobs into batches, keeping each integration atomic unless it exceeds capacity.

    An integration that fits a batch is never split: it is appended to the current batch when it
    fits the remainder, otherwise a fresh batch is started for it. An integration whose job count
    exceeds ``capacity`` raises :class:`PlanningError` unless ``allow_integration_splitting`` is
    set, in which case it spills across capacity-bounded batches and its final partial batch stays
    open for following integrations.

    Accepts any ``Sequence`` at this public boundary; the input is normalized to a list once and
    all internal grouping/chunking operates on lists.
    """
    batches: list[list[BatchJob]] = []
    current: list[BatchJob] = []

    for group in _group_by_integration(list(jobs)):
        if len(group) > capacity:
            if not config.allow_integration_splitting:
                raise PlanningError(
                    f"Integration {group[0].target!r} needs {len(group)} jobs, exceeding the batch "
                    f"capacity of {capacity}; enable allow_integration_splitting to span multiple batches."
                )
            # Spill the oversized integration across full, capacity-bounded batches, combined with
            # the current remainder so no capacity is wasted. The final chunk stays open as the new
            # current batch so following integrations can reuse its remaining slots.
            # strict=False: the final chunk is the remainder and is intentionally allowed to be
            # shorter than capacity.
            *full, current = map(list, batched(chain(current, group), capacity, strict=False))
            batches.extend(full)
        elif len(current) + len(group) <= capacity:
            current.extend(group)
        else:
            # The integration fits a batch but not the current remainder; start a fresh batch for
            # it. current is non-empty here (an empty current would satisfy the branch above).
            batches.append(current)
            current = list(group)

    if current:
        batches.append(current)
    return batches


def _group_by_integration(jobs: list[BatchJob]) -> list[list[BatchJob]]:
    """Group jobs by integration (``target``), preserving first-appearance order."""
    groups: dict[str, list[BatchJob]] = {}
    for job in jobs:
        groups.setdefault(job.target, []).append(job)
    return list(groups.values())
