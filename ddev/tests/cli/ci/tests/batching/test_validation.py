# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the strategy-independent validation of a batch partition."""

from __future__ import annotations

import dataclasses

import pytest

from ddev.cli.ci.tests.batching.exceptions import BatchValidationError
from ddev.cli.ci.tests.batching.strategy import default_strategy
from ddev.cli.ci.tests.batching.validation import validate_batches
from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
from ddev.cli.ci.tests.messages import BatchJob
from tests.helpers.batching import jobs, make_job


def config(*, capacity: int = 240, allow_integration_splitting: bool = False) -> BatchingConfig:
    return BatchingConfig(max_jobs_per_batch=capacity, allow_integration_splitting=allow_integration_splitting)


def test_validate_accepts_default_strategy_output():
    all_jobs = jobs("postgres", 200) + jobs("mysql", 100)
    groups = default_strategy(all_jobs, config=config())
    validate_batches(groups, all_jobs, config=config())  # does not raise


def test_validate_rejects_empty_batch():
    all_jobs = jobs("postgres", 2)
    with pytest.raises(BatchValidationError, match="empty"):
        validate_batches([all_jobs, []], all_jobs, config=config())


def test_validate_rejects_overfilled_batch():
    all_jobs = jobs("postgres", 5)
    with pytest.raises(BatchValidationError, match="capacity"):
        validate_batches([all_jobs], all_jobs, config=config(capacity=4))


def test_validate_rejects_lost_job():
    all_jobs = jobs("postgres", 3)
    with pytest.raises(BatchValidationError, match="exactly once"):
        validate_batches([all_jobs[:2]], all_jobs, config=config())


def test_validate_rejects_a_job_duplicated_across_batches():
    all_jobs = jobs("postgres", 2)
    with pytest.raises(BatchValidationError, match="exactly once"):
        validate_batches([[all_jobs[0]], [all_jobs[0], all_jobs[1]]], all_jobs, config=config())


def test_validate_compares_jobs_by_value_not_identity():
    # A strategy is free to rebuild equal jobs rather than pass the original instances through.
    all_jobs = jobs("postgres", 3)
    rebuilt = [dataclasses.replace(job) for job in all_jobs]

    validate_batches([rebuilt], all_jobs, config=config())  # does not raise


def test_validate_rejects_duplicate_names_within_batch():
    clash = jobs("postgres", 1)[0]
    twin = make_job(clash.name, target="mysql", environment="py3.11")
    all_jobs = [clash, twin]
    with pytest.raises(BatchValidationError, match="duplicate job name"):
        validate_batches([[clash, twin]], all_jobs, config=config())


def test_validate_rejects_duplicate_artifact_identity_within_batch():
    # Two jobs with distinct display names but the same target/facet/environment/platform collapse
    # to the same artifact identity; central validation must reject them even though names differ.
    def artifact_twin(name: str) -> BatchJob:
        return make_job(name, target="postgres", environment="py3.11")

    a, b = artifact_twin("postgres (py3.11)"), artifact_twin("postgres duplicate")
    assert a.name != b.name
    assert a.artifact_name() == b.artifact_name()

    with pytest.raises(BatchValidationError, match="duplicate artifact identities"):
        validate_batches([[a, b]], [a, b], config=config())


def test_validate_rejects_illegal_split_when_disabled():
    all_jobs = jobs("postgres", 4)
    with pytest.raises(BatchValidationError, match="split"):
        validate_batches([all_jobs[:2], all_jobs[2:]], all_jobs, config=config())


def test_validate_rejects_split_of_fitting_integration_even_when_enabled():
    # Splitting is enabled, but this integration fits capacity, so splitting it is still invalid.
    all_jobs = jobs("postgres", 4)
    with pytest.raises(BatchValidationError, match="fits in one batch"):
        validate_batches([all_jobs[:2], all_jobs[2:]], all_jobs, config=config(allow_integration_splitting=True))


def test_validate_allows_oversized_split_when_enabled():
    all_jobs = jobs("huge", 400)
    groups = default_strategy(all_jobs, config=config(allow_integration_splitting=True))
    validate_batches(groups, all_jobs, config=config(allow_integration_splitting=True))  # no raise
