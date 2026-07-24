# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Strategy-independent validation of a batch partition.

:func:`validate_batches` enforces the execution contract regardless of which strategy produced the
partition, so a custom injected callable cannot silently drop, duplicate, overfill, illegally
split, or emit identity-colliding batches. It is a ``batching``-level concern (invoked by
:mod:`~ddev.cli.ci.tests.batching.build`), not part of any single strategy, so every strategy is
held to the same contract.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.batching.exceptions import BatchValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import BatchJob


def validate_batches(
    job_groups: Sequence[Sequence[BatchJob]],
    jobs: Sequence[BatchJob],
    *,
    capacity: int,
    config: BatchingConfig,
):
    """Enforce the batch-execution contract independently of the strategy that produced it.

    Rejects empty or over-capacity batches, duplicate job names or artifact identities within a
    batch, any deviation from exact once-per-job coverage of ``jobs``, and integration splitting
    that is not justified by the configured oversized-integration condition.

    Artifact identity (``BatchJob.artifact_name``) is checked in addition to the display name
    because sanitization or ambiguous environment labels can collapse two distinct-named jobs onto
    the same artifact, which would let their uploaded/organized files overwrite one another even
    though their names differ.
    """
    for index, group in enumerate(job_groups):
        if not group:
            raise BatchValidationError(f"Batch at index {index} is empty.")
        if len(group) > capacity:
            raise BatchValidationError(f"Batch at index {index} has {len(group)} jobs, exceeding capacity {capacity}.")
        names = [job.name for job in group]
        if len(names) != len(set(names)):
            raise BatchValidationError(f"Batch at index {index} has duplicate job names.")
        artifact_names = [job.artifact_name() for job in group]
        if len(artifact_names) != len(set(artifact_names)):
            raise BatchValidationError(f"Batch at index {index} has duplicate artifact identities.")

    _validate_coverage(job_groups, jobs)
    _validate_splitting(job_groups, jobs, capacity=capacity, config=config)


def _validate_coverage(job_groups: Sequence[Sequence[BatchJob]], jobs: Sequence[BatchJob]):
    planned = [job for group in job_groups for job in group]
    planned_counts = Counter(id(job) for job in planned)
    if any(count > 1 for count in planned_counts.values()):
        raise BatchValidationError("Planned batches contain duplicate jobs.")
    if set(planned_counts) != {id(job) for job in jobs}:
        raise BatchValidationError("Planned batches must cover every input job exactly once.")


def _validate_splitting(
    job_groups: Sequence[Sequence[BatchJob]],
    jobs: Sequence[BatchJob],
    *,
    capacity: int,
    config: BatchingConfig,
):
    target_counts = Counter(job.target for job in jobs)
    batches_per_target: dict[str, set[int]] = {}
    for index, group in enumerate(job_groups):
        for job in group:
            batches_per_target.setdefault(job.target, set()).add(index)

    for target, indices in batches_per_target.items():
        if len(indices) <= 1:
            continue
        if not config.allow_integration_splitting:
            raise BatchValidationError(
                f"Integration {target!r} is split across batches but integration splitting is disabled."
            )
        if target_counts[target] <= capacity:
            raise BatchValidationError(
                f"Integration {target!r} fits in one batch ({target_counts[target]} <= {capacity}) but was split."
            )
