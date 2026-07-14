# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Iterator

import pytest

from datadog_checks.base.types import InstanceType


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[InstanceType]:
    yield INSTANCE


# Small, fast configuration so the test suite exercises the full engine quickly.
INSTANCE: InstanceType = {
    'num_workers': 4,
    'allocations_per_worker': 16,
    'min_alloc_bytes': 512,
    'max_alloc_bytes': 65536,
    'retained_fraction': 0.25,
    'max_retained_bytes': 8 * 1024 * 1024,
    'max_total_bytes': 64 * 1024 * 1024,
    'thread_churn_per_run': 2,
    'run_budget_seconds': 1,
}


@pytest.fixture
def instance() -> InstanceType:
    return dict(INSTANCE)
