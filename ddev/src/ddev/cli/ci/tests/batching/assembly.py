# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Strategy-independent construction of ``TestBatch`` messages from a validated partition.

Message construction is a ``batching``-level concern (invoked by
:mod:`~ddev.cli.ci.tests.batching.build`), not part of any single strategy, so it applies uniformly
to every strategy's output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.cli.ci.tests.messages import TestBatch

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.messages import BatchJob


def create_test_batches(job_groups: Sequence[Sequence[BatchJob]]) -> list[TestBatch]:
    """Build ordered ``TestBatch`` messages with function-local deterministic numbering.

    Numbering restarts at ``batch-01`` on every call, so identical inputs always yield the same
    ordered ids. The logical ``batch_id`` is also used as the message ``id`` here; downstream
    processors correlate on ``batch_id``, keeping the message identity free to diverge later.
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
