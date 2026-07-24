# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The injectable batching-strategy extension contract.

A batching strategy maps an ordered list of concrete jobs to an ordered list of job groups (one
per batch). Keeping the protocol separate lets new strategies depend on the contract without
importing the default implementation or strategy-independent validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import BatchJob


class BatchStrategy(Protocol):
    """Maps an ordered list of jobs to an ordered list of capacity-bounded job groups."""

    def __call__(
        self,
        jobs: Sequence[BatchJob],
        *,
        capacity: int,
        config: BatchingConfig,
    ) -> list[list[BatchJob]]: ...
