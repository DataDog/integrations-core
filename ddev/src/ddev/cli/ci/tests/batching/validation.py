# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Validation of a batch partition, applied to every strategy's output."""

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
    config: BatchingConfig,
):
    """Enforce the batch-execution contract, so no strategy can emit an unrunnable plan.

    Rejects empty or over-capacity batches, duplicate job names or artifact identities within a
    batch, any deviation from exact once-per-job coverage of `jobs`, and unjustified integration
    splitting.

    Artifact identity is checked as well as the display name because sanitization can collapse two
    differently named jobs onto one artifact, whose files would then overwrite each other.
    """
    capacity = config.max_jobs_per_batch
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
    """Require the partition to contain every input job exactly once, compared by value.

    By value, not identity, so a strategy may rebuild equal jobs instead of passing the original
    instances through.
    """
    planned = Counter(job for group in job_groups for job in group)
    expected = Counter(jobs)
    if planned != expected:
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
