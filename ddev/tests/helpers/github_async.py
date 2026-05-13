# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Test helpers for the async GitHub client.

Provides a `FakeAsyncGitHubClient` that records every call and lets tests
register canned responses with `mock_response`, plus a `fake_async_github`
pytest fixture that patches `async_github_client` to yield the fake.

Quick reference:

    def test_thing(fake_async_github):
        # Sticky default for all matching calls
        fake_async_github.mock_response(
            'create_pull_request',
            PullRequest(number=5, html_url='https://github.com/x/pr/5'),
        )

        # Partial match: only PR #5 gets the override
        fake_async_github.mock_response(
            'add_labels_to_issue',
            httpx.HTTPStatusError(...),
            issue_number=5,
        )

        # FIFO queue: first matching call raises, second succeeds
        fake_async_github.mock_response('create_pull_request', err, once=True)
        fake_async_github.mock_response('create_pull_request', pr_response, once=True)

        do_thing_under_test()
        fake_async_github.assert_called_with('create_pull_request', ...)
        fake_async_github.assert_all_responses_consumed()
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import pytest
from pytest_mock import MockerFixture

from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import PullRequest


@dataclass
class RecordedRequest:
    """A single recorded call to the fake client."""

    method: str
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class _MockEntry:
    """A single registered response, either sticky or one-shot."""

    response: Any
    match_kwargs: dict[str, Any]
    once: bool


def _default_response_factories() -> dict[str, Callable[[], Any]]:
    """Built-in default responses used when no `mock_response` matches a call."""
    return {
        'create_pull_request': lambda: GitHubResponse(
            data=PullRequest(number=1, html_url='https://github.com/test/repo/pull/1'),
            headers={},
        ),
        'add_labels_to_issue': lambda: GitHubResponse.model_validate({'data': None, 'headers': {}}),
    }


class FakeAsyncGitHubClient:
    """Test double for AsyncGitHubClient that records calls and serves canned responses.

    Mock responses are registered via `mock_response`. Each call to a mirrored API method
    consults, in order:

    1. The one-shot queue for that method (FIFO, first match wins, consumed on use).
    2. The sticky-mock list for that method (most-recent registration wins).
    3. A built-in default response (see `_default_response_factories`).

    Exceptions registered as responses are raised. Plain data values are auto-wrapped in
    `GitHubResponse(data=value, headers={})`. Full `GitHubResponse` instances pass through.
    """

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self._oneshot_mocks: dict[str, list[_MockEntry]] = {}
        self._sticky_mocks: dict[str, list[_MockEntry]] = {}
        self._default_response_factories: dict[str, Callable[[], Any]] = _default_response_factories()

    # ------------------------------------------------------------------
    # Mock registration
    # ------------------------------------------------------------------

    def mock_response(
        self,
        method: str,
        response: Any,
        /,
        *,
        once: bool = False,
        **match_kwargs: Any,
    ) -> None:
        """Register *response* to be returned by *method*.

        Args:
            method: Name of the client method to stub (e.g. ``'create_pull_request'``).
            response: What to return. Behavior depends on its type:
                - ``BaseException`` instance -> raised when the call is made.
                - ``GitHubResponse`` instance -> returned as-is.
                - Anything else (including ``None``) -> wrapped in
                  ``GitHubResponse(data=response, headers={})``.
            once: When True, this response is consumed by the first matching call
                (FIFO across all one-shots registered for the method). Otherwise the
                response is sticky and fires on every matching call until something
                more specific is registered.
            **match_kwargs: Optional key/value pairs that the call's recorded kwargs
                must contain (partial match). With no kwargs, the response matches any
                call to *method*.
        """
        entry = _MockEntry(response=response, match_kwargs=match_kwargs, once=once)
        bucket = self._oneshot_mocks if once else self._sticky_mocks
        bucket.setdefault(method, []).append(entry)

    # ------------------------------------------------------------------
    # Mirrored API surface
    # ------------------------------------------------------------------

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = '',
        draft: bool = False,
        timeout: float | None = None,
    ) -> GitHubResponse[PullRequest]:
        return self._call(
            'create_pull_request',
            owner=owner,
            repo=repo,
            title=title,
            head=head,
            base=base,
            body=body,
            draft=draft,
        )

    async def add_labels_to_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: list[str],
        timeout: float | None = None,
    ) -> GitHubResponse[None]:
        return self._call(
            'add_labels_to_issue',
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            labels=labels,
        )

    async def aclose(self) -> None:
        return None

    # ------------------------------------------------------------------
    # Inspection / assertions
    # ------------------------------------------------------------------

    def calls_to(self, method: str) -> list[RecordedRequest]:
        """Return every recorded call to *method*."""
        return [r for r in self.requests if r.method == method]

    def last_call(self, method: str) -> RecordedRequest:
        """Return the most recent recorded call to *method*, raising if there are none.

        Use when strict full-kwargs assertion is too tedious (e.g. a long PR body) and
        you want to inspect individual fields with plain asserts.
        """
        calls = self.calls_to(method)
        if not calls:
            raise AssertionError(f'No calls to {method!r} were recorded.')
        return calls[-1]

    def assert_called_with(self, method: str, **expected_kwargs: Any) -> RecordedRequest:
        """Assert *method* was called at least once with EXACTLY *expected_kwargs*.

        Strict equality: every keyword the implementation passed must appear in
        *expected_kwargs* and vice versa. Missing or extra keys both fail. Returns
        the first matching call.
        """
        matches = [r for r in self.calls_to(method) if r.kwargs == expected_kwargs]
        if not matches:
            raise AssertionError(
                f'No call to {method!r} matched {expected_kwargs!r}. Recorded calls: {self.calls_to(method)}'
            )
        return matches[0]

    def assert_called_once_with(self, method: str, **expected_kwargs: Any) -> RecordedRequest:
        """Assert *method* was called exactly once with EXACTLY *expected_kwargs*.

        Strict equality, mirrors `Mock.assert_called_once_with`.
        """
        calls = self.calls_to(method)
        matches = [r for r in calls if r.kwargs == expected_kwargs]
        if len(calls) != 1 or len(matches) != 1:
            raise AssertionError(
                f'Expected exactly one call to {method!r} with {expected_kwargs!r}; '
                f'got {len(calls)} call(s), {len(matches)} matching. Recorded calls: {calls}'
            )
        return matches[0]

    def assert_not_called(self, method: str) -> None:
        """Assert that *method* was never called."""
        calls = self.calls_to(method)
        if calls:
            raise AssertionError(f'Expected no calls to {method!r}, but got: {calls}')

    def assert_all_responses_consumed(self) -> None:
        """Assert every one-shot mock registered has been consumed by a call.

        Use in tests that depend on a queued sequence firing (e.g. retry logic). Sticky
        mocks are not affected; only one-shots are tracked.
        """
        pending = {method: queue for method, queue in self._oneshot_mocks.items() if queue}
        if pending:
            details = '; '.join(f'{method}: {len(queue)} remaining' for method, queue in pending.items())
            raise AssertionError(f'One-shot responses were not consumed -> {details}')

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _record(self, method: str, **kwargs: Any) -> None:
        self.requests.append(RecordedRequest(method=method, kwargs=kwargs))

    def _call(self, method: str, **call_kwargs: Any) -> Any:
        self._record(method, **call_kwargs)
        response = self._resolve_response(method, call_kwargs)
        if isinstance(response, BaseException):
            raise response
        if isinstance(response, GitHubResponse):
            return response
        return GitHubResponse.model_validate({'data': response, 'headers': {}})

    def _resolve_response(self, method: str, call_kwargs: dict[str, Any]) -> Any:
        # 1. One-shot queue: FIFO, first match wins, consumed.
        queue = self._oneshot_mocks.get(method, [])
        for i, entry in enumerate(queue):
            if self._matches(call_kwargs, entry.match_kwargs):
                queue.pop(i)
                return entry.response

        # 2. Sticky mocks: most-recent registration wins.
        for entry in reversed(self._sticky_mocks.get(method, [])):
            if self._matches(call_kwargs, entry.match_kwargs):
                return entry.response

        # 3. Built-in default for this method.
        factory = self._default_response_factories.get(method)
        if factory is None:
            raise AssertionError(
                f'No mock registered for {method!r} and no built-in default. '
                f'Call fake_async_github.mock_response({method!r}, ...) in your test.'
            )
        return factory()

    @staticmethod
    def _matches(call_kwargs: dict[str, Any], match_kwargs: dict[str, Any]) -> bool:
        return all(call_kwargs.get(k) == v for k, v in match_kwargs.items())


@pytest.fixture
def fake_async_github(mocker: MockerFixture) -> FakeAsyncGitHubClient:
    """Patch `async_github_client` to yield a `FakeAsyncGitHubClient` and stub the token."""
    fake = FakeAsyncGitHubClient()

    @asynccontextmanager
    async def fake_context(
        token: str | None = None,
        default_timeout: float = 30.0,
        transport: Any = None,
    ) -> AsyncIterator[FakeAsyncGitHubClient]:
        yield fake

    mocker.patch('ddev.utils.github_async.client.async_github_client', fake_context)
    mocker.patch('ddev.utils.github_async.async_github_client', fake_context)
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': 'ghp_test'})
    return fake
