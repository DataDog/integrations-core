# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the default batching strategy, central validation, and message construction."""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.batching.assembly import create_test_batches
from ddev.cli.ci.tests.batching.exceptions import BatchValidationError, PlanningError
from ddev.cli.ci.tests.batching.strategy import default_strategy
from ddev.cli.ci.tests.batching.validation import validate_batches
from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
from ddev.cli.ci.tests.messages import BatchJob, Platform


def jobs(target: str, count: int) -> list[BatchJob]:
    # Each job carries a distinct environment, as production jobs within an integration do, so
    # names and artifact identities are unique within the target.
    return [
        BatchJob(
            name=f"{target}-{index}",
            target=target,
            runner_labels=("ubuntu-22.04",),
            environment=f"env-{index}",
            platform=Platform.LINUX,
            unit_tests=True,
            e2e_tests=False,
        )
        for index in range(count)
    ]


def config(*, capacity: int = 240, allow_integration_splitting: bool = False) -> BatchingConfig:
    return BatchingConfig(max_jobs_per_batch=capacity, allow_integration_splitting=allow_integration_splitting)


def sizes(groups: list[list[BatchJob]]) -> list[int]:
    return [len(group) for group in groups]


# ---------------------------------------------------------------------------
# default_strategy
# ---------------------------------------------------------------------------


def test_empty_input_returns_no_groups():
    assert default_strategy([], capacity=240, config=config()) == []


def test_single_integration_fits_in_one_batch():
    groups = default_strategy(jobs("postgres", 100), capacity=240, config=config())
    assert sizes(groups) == [100]


def test_two_fitting_integrations_at_capacity_210_do_not_split():
    # 200 + 200 at capacity 210: two non-overflowing batches, neither integration split.
    all_jobs = jobs("postgres", 200) + jobs("mysql", 200)
    groups = default_strategy(all_jobs, capacity=210, config=config(capacity=210))

    assert sizes(groups) == [200, 200]
    assert {job.target for job in groups[0]} == {"postgres"}
    assert {job.target for job in groups[1]} == {"mysql"}


def test_fitting_integration_starts_new_batch_rather_than_filling_remainder():
    # postgres (100) fills the first batch; mysql (150) does not fit the 110-job remainder, so it
    # starts a new batch instead of being split to fill it.
    all_jobs = jobs("postgres", 100) + jobs("mysql", 150)
    groups = default_strategy(all_jobs, capacity=210, config=config(capacity=210))

    assert sizes(groups) == [100, 150]


def test_small_integrations_pack_together():
    all_jobs = jobs("a", 80) + jobs("b", 80) + jobs("c", 80) + jobs("d", 80)
    groups = default_strategy(all_jobs, capacity=240, config=config())

    # a+b+c fill the first batch (240); d starts the next.
    assert sizes(groups) == [240, 80]
    assert {job.target for job in groups[0]} == {"a", "b", "c"}
    assert {job.target for job in groups[1]} == {"d"}


def test_oversized_integration_fails_when_splitting_disabled():
    with pytest.raises(PlanningError, match="exceeding the batch capacity"):
        default_strategy(jobs("huge", 400), capacity=240, config=config(allow_integration_splitting=False))


def test_oversized_integration_spills_across_capacity_bounded_batches_when_enabled():
    # Canonical case: 400 jobs at capacity 240 occupy 240 then 160.
    groups = default_strategy(jobs("huge", 400), capacity=240, config=config(allow_integration_splitting=True))

    assert sizes(groups) == [240, 160]


def test_oversized_remainder_is_reusable_by_following_integrations():
    # The 80 free slots left in the second batch by the 400-job integration are used by the next.
    all_jobs = jobs("huge", 400) + jobs("small", 80)
    groups = default_strategy(all_jobs, capacity=240, config=config(allow_integration_splitting=True))

    assert sizes(groups) == [240, 240]
    assert {job.target for job in groups[0]} == {"huge"}
    assert {job.target for job in groups[1]} == {"huge", "small"}
    # "small" fit entirely into the remainder, so it is not itself split.
    assert sum(1 for job in groups[1] if job.target == "small") == 80


# ---------------------------------------------------------------------------
# validate_batches
# ---------------------------------------------------------------------------


def test_validate_accepts_default_strategy_output():
    all_jobs = jobs("postgres", 200) + jobs("mysql", 100)
    groups = default_strategy(all_jobs, capacity=240, config=config())
    validate_batches(groups, all_jobs, capacity=240, config=config())  # does not raise


def test_validate_rejects_empty_batch():
    all_jobs = jobs("postgres", 2)
    with pytest.raises(BatchValidationError, match="empty"):
        validate_batches([all_jobs, []], all_jobs, capacity=240, config=config())


def test_validate_rejects_overfilled_batch():
    all_jobs = jobs("postgres", 5)
    with pytest.raises(BatchValidationError, match="capacity"):
        validate_batches([all_jobs], all_jobs, capacity=4, config=config())


def test_validate_rejects_lost_job():
    all_jobs = jobs("postgres", 3)
    with pytest.raises(BatchValidationError, match="exactly once"):
        validate_batches([all_jobs[:2]], all_jobs, capacity=240, config=config())


def test_validate_rejects_duplicated_job():
    all_jobs = jobs("postgres", 2)
    with pytest.raises(BatchValidationError, match="duplicate"):
        validate_batches([[all_jobs[0], all_jobs[0], all_jobs[1]]], all_jobs, capacity=240, config=config())


def test_validate_rejects_duplicate_names_within_batch():
    clash = jobs("postgres", 1)[0]
    twin = BatchJob(
        name=clash.name,
        target="mysql",
        runner_labels=("ubuntu-22.04",),
        environment="py3.11",
        platform=Platform.LINUX,
        unit_tests=True,
        e2e_tests=False,
    )
    all_jobs = [clash, twin]
    with pytest.raises(BatchValidationError, match="duplicate job name"):
        validate_batches([[clash, twin]], all_jobs, capacity=240, config=config())


def test_validate_rejects_duplicate_artifact_identity_within_batch():
    # Two jobs with distinct display names but the same target/facet/environment/platform collapse
    # to the same artifact identity; central validation must reject them even though names differ.
    def artifact_twin(name: str) -> BatchJob:
        return BatchJob(
            name=name,
            target="postgres",
            runner_labels=("ubuntu-22.04",),
            environment="py3.11",
            platform=Platform.LINUX,
            unit_tests=True,
            e2e_tests=False,
        )

    a, b = artifact_twin("postgres (py3.11)"), artifact_twin("postgres duplicate")
    assert a.name != b.name
    assert a.artifact_name() == b.artifact_name()

    with pytest.raises(BatchValidationError, match="duplicate artifact identities"):
        validate_batches([[a, b]], [a, b], capacity=240, config=config())


def test_validate_rejects_illegal_split_when_disabled():
    all_jobs = jobs("postgres", 4)
    with pytest.raises(BatchValidationError, match="split"):
        validate_batches([all_jobs[:2], all_jobs[2:]], all_jobs, capacity=240, config=config())


def test_validate_rejects_split_of_fitting_integration_even_when_enabled():
    # Splitting is enabled, but this integration fits capacity, so splitting it is still invalid.
    all_jobs = jobs("postgres", 4)
    with pytest.raises(BatchValidationError, match="fits in one batch"):
        validate_batches(
            [all_jobs[:2], all_jobs[2:]], all_jobs, capacity=240, config=config(allow_integration_splitting=True)
        )


def test_validate_allows_oversized_split_when_enabled():
    all_jobs = jobs("huge", 400)
    groups = default_strategy(all_jobs, capacity=240, config=config(allow_integration_splitting=True))
    validate_batches(groups, all_jobs, capacity=240, config=config(allow_integration_splitting=True))  # no raise


# ---------------------------------------------------------------------------
# create_test_batches
# ---------------------------------------------------------------------------


def test_create_test_batches_numbers_and_populates_messages():
    groups = [jobs("postgres", 2), jobs("mysql", 1) + jobs("redis", 1)]

    batches = create_test_batches(groups)

    assert [b.batch_id for b in batches] == ["batch-01", "batch-02"]
    assert [b.id for b in batches] == ["batch-01", "batch-02"]
    assert [b.jobs_count for b in batches] == [2, 2]
    assert batches[0].integrations == ["postgres"]
    assert batches[1].integrations == ["mysql", "redis"]


def test_create_test_batches_numbering_is_local_and_repeatable():
    groups = [jobs("a", 1), jobs("b", 1), jobs("c", 1)]

    first = [b.batch_id for b in create_test_batches(groups)]
    second = [b.batch_id for b in create_test_batches(groups)]

    assert first == second == ["batch-01", "batch-02", "batch-03"]
