# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Construction of `TestBatch` messages from a validated partition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.cli.ci.tests.messages import TestBatch

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.messages import BatchJob


def create_test_batches(job_groups: Sequence[Sequence[BatchJob]]) -> list[TestBatch]:
    """Build ordered `TestBatch` messages, numbering from `batch-01` on every call.

    The message `id` is set to the same value as `batch_id` for now; processors correlate on
    `batch_id`, so the two are free to diverge later.
    """
    batches: list[TestBatch] = []
    for index, group in enumerate(job_groups, start=1):
        batch_id = f"batch-{index:02d}"
        integrations = list(dict.fromkeys(job.target for job in group))
        batches.append(
            TestBatch(
                id=batch_id,
                batch_id=batch_id,
                job_list=list(group),
                jobs_count=len(group),
                integrations=integrations,
            )
        )
    return batches
