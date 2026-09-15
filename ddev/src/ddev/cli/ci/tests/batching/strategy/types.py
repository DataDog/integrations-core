# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The batching-strategy contract, kept separate so a strategy need not import the default one."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import BatchJob


class BatchStrategy(Protocol):
    """Maps an ordered list of jobs to an ordered list of capacity-bounded job groups."""

    def __call__(self, jobs: Sequence[BatchJob], *, config: BatchingConfig) -> list[list[BatchJob]]: ...
