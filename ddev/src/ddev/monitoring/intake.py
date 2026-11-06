# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Count-bounded request buffering and HTTP-413 recovery shared by the Datadog exporters."""

from __future__ import annotations

from collections.abc import Callable

from datadog_api_client.exceptions import ApiException

PAYLOAD_TOO_LARGE = 413


class SubmissionStopped(Exception):
    """Raised when the shutdown deadline stops a submission before it starts."""


def submit_intake_batch[T](
    items: list[T],
    submit: Callable[[list[T]], None],
    *,
    on_rejected: Callable[[T], None],
    should_stop: Callable[[], bool] = lambda: False,
) -> None:
    """Submit *items* as one request, answering an HTTP 413 by splitting the rejected list.

    The server is the authority on payload size: a rejected batch is bisected and both halves
    are submitted on their own. A single item the API still rejects is indivisible, so it is
    reported through *on_rejected* without stopping its siblings. Other errors propagate to
    the caller.
    """
    if not items:
        return
    if should_stop():
        raise SubmissionStopped('the shutdown deadline stopped the submission before it started')
    try:
        submit(items)
        return
    except ApiException as error:
        if error.status != PAYLOAD_TOO_LARGE:
            raise
    if len(items) == 1:
        on_rejected(items[0])
        return
    split = len(items) // 2
    submit_intake_batch(items[:split], submit, on_rejected=on_rejected, should_stop=should_stop)
    submit_intake_batch(items[split:], submit, on_rejected=on_rejected, should_stop=should_stop)


class RequestBatch[T]:
    """Buffer items and submit them in count-bounded requests."""

    def __init__(self, submit: Callable[[list[T]], None], *, item_limit: int) -> None:
        self._submit = submit
        self._item_limit = item_limit
        self._items: list[T] = []

    def add(self, item: T) -> None:
        self._items.append(item)
        if len(self._items) >= self._item_limit:
            self.flush()

    def flush(self) -> None:
        items, self._items = self._items, []
        if items:
            self._submit(items)
