# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the default batching strategy."""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.batching.exceptions import PlanningError
from ddev.cli.ci.tests.batching.strategy import default_strategy
from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
from ddev.cli.ci.tests.messages import BatchJob
from tests.cli.ci.tests.helpers import jobs


def config(*, capacity: int = 240, allow_integration_splitting: bool = False) -> BatchingConfig:
    return BatchingConfig(max_jobs_per_batch=capacity, allow_integration_splitting=allow_integration_splitting)


def sizes(groups: list[list[BatchJob]]) -> list[int]:
    return [len(group) for group in groups]


# ---------------------------------------------------------------------------
# default_strategy
# ---------------------------------------------------------------------------


def test_empty_input_returns_no_groups():
    assert default_strategy([], config=config()) == []


@pytest.mark.parametrize(
    ("groups", "capacity", "expected_sizes", "expected_targets"),
    [
        pytest.param(
            [("postgres", 200), ("mysql", 200)],
            210,
            [200, 200],
            [{"postgres"}, {"mysql"}],
            id="fitting-integrations-never-share-a-batch",
        ),
        pytest.param(
            [("postgres", 100), ("mysql", 150)],
            210,
            [100, 150],
            [{"postgres"}, {"mysql"}],
            id="a-remainder-too-small-is-left-unfilled",
        ),
        pytest.param(
            [("a", 80), ("b", 80), ("c", 80), ("d", 80)],
            240,
            [240, 80],
            [{"a", "b", "c"}, {"d"}],
            id="small-integrations-pack-together",
        ),
    ],
)
def test_default_strategy_packing(groups, capacity, expected_sizes, expected_targets):
    all_jobs = [job for target, count in groups for job in jobs(target, count)]

    result = default_strategy(all_jobs, config=config(capacity=capacity))

    assert sizes(result) == expected_sizes
    assert [{job.target for job in group} for group in result] == expected_targets


def test_oversized_integration_fails_when_splitting_disabled():
    with pytest.raises(PlanningError, match="exceeding the batch capacity"):
        default_strategy(jobs("huge", 400), config=config(allow_integration_splitting=False))


def test_oversized_integration_spills_across_capacity_bounded_batches_when_enabled():
    # Canonical case: 400 jobs at capacity 240 occupy 240 then 160.
    groups = default_strategy(jobs("huge", 400), config=config(allow_integration_splitting=True))

    assert sizes(groups) == [240, 160]


def test_oversized_remainder_is_reusable_by_following_integrations():
    # The 80 free slots left in the second batch by the 400-job integration are used by the next.
    all_jobs = jobs("huge", 400) + jobs("small", 80)
    groups = default_strategy(all_jobs, config=config(allow_integration_splitting=True))

    assert sizes(groups) == [240, 240]
    assert {job.target for job in groups[0]} == {"huge"}
    assert {job.target for job in groups[1]} == {"huge", "small"}
    # "small" fit entirely into the remainder, so it is not itself split.
    assert sum(1 for job in groups[1] if job.target == "small") == 80


def test_oversized_integration_spills_starting_from_an_open_batch():
    # The open batch is filled before the oversized integration starts a new one, so no slot is
    # wasted: 80 + 400 at capacity 240 packs as 240 then 240 rather than 80 then 240 then 160.
    all_jobs = jobs("small", 80) + jobs("huge", 400)

    groups = default_strategy(all_jobs, config=config(allow_integration_splitting=True))

    assert sizes(groups) == [240, 240]
    assert {job.target for job in groups[0]} == {"small", "huge"}
    assert {job.target for job in groups[1]} == {"huge"}
