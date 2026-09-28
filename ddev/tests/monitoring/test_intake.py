# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Partition behavior of the shared HTTP-413 recovery and request buffering."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from datadog_api_client.exceptions import ApiException

from ddev.monitoring.intake import RequestBatch, SubmissionStopped, submit_intake_batch


def rejecting_submit(too_large: Callable[[list[str]], bool]) -> tuple[Callable[[list[str]], None], list[list[str]]]:
    """A submission callback that records every attempt and rejects batches matching a rule."""
    attempts: list[list[str]] = []

    def submit(items: list[str]) -> None:
        attempts.append(list(items))
        if too_large(items):
            raise ApiException(status=413, reason='Payload Too Large')

    return submit, attempts


def test_a_rejected_batch_is_split_until_the_api_accepts_every_item():
    submit, attempts = rejecting_submit(lambda items: len(items) > 2)

    submit_intake_batch(['a', 'b', 'c', 'd', 'e'], submit, on_rejected=lambda item: None)

    accepted = [batch for batch in attempts if len(batch) <= 2]
    assert [item for batch in accepted for item in batch] == ['a', 'b', 'c', 'd', 'e']
    assert attempts[0] == ['a', 'b', 'c', 'd', 'e']


def test_an_item_the_api_rejects_alone_is_reported_without_losing_its_siblings():
    submit, attempts = rejecting_submit(lambda items: 'bad' in items)
    rejected: list[str] = []

    submit_intake_batch(['ok-1', 'bad', 'ok-2'], submit, on_rejected=rejected.append)

    accepted = [batch for batch in attempts if 'bad' not in batch]
    assert [item for batch in accepted for item in batch] == ['ok-1', 'ok-2']
    assert rejected == ['bad']


@pytest.mark.parametrize(
    'error', [RuntimeError('intake unavailable'), ApiException(status=500)], ids=['runtime', 'api']
)
def test_failures_other_than_413_propagate_to_the_caller(error: Exception):
    def submit(items: list[str]) -> None:
        raise error

    with pytest.raises(type(error)):
        submit_intake_batch(['a', 'b'], submit, on_rejected=lambda item: None)


def test_the_deadline_stops_a_submission_before_it_starts():
    attempts: list[list[str]] = []

    def submit(items: list[str]) -> None:
        attempts.append(list(items))

    with pytest.raises(SubmissionStopped):
        submit_intake_batch(['a', 'b'], submit, on_rejected=lambda item: None, should_stop=lambda: True)

    assert attempts == []


def test_the_deadline_stops_the_halves_of_a_rejected_batch():
    submit, attempts = rejecting_submit(lambda items: True)

    def should_stop() -> bool:
        return bool(attempts)

    with pytest.raises(SubmissionStopped):
        submit_intake_batch(['a', 'b', 'c'], submit, on_rejected=lambda item: None, should_stop=should_stop)

    # The whole batch was tried once; neither half started a request of its own.
    assert attempts == [['a', 'b', 'c']]


def test_a_batch_submits_as_soon_as_it_reaches_its_capacity():
    submitted: list[list[str]] = []

    batch = RequestBatch(submitted.append, item_limit=2)
    batch.add('a')

    assert submitted == []

    batch.add('b')

    assert submitted == [['a', 'b']]
