# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Test helpers for the async GitHub client.

Provides a `FakeAsyncGitHubClient` that records every call and exposes
assertion helpers, plus a `fake_async_github` pytest fixture that patches
`async_github_client` to yield the fake and sets a stub token.

Usage:

    def test_thing(fake_async_github):
        do_something_that_creates_a_pr()
        fake_async_github.assert_called(
            'create_pull_request', title='[Backport] Fix bug', draft=False
        )
"""

from __future__ import annotations

from collections.abc import AsyncIterator
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


class FakeAsyncGitHubClient:
    """Test double for AsyncGitHubClient that records calls and returns canned responses.

    Override response shape by assigning to `pull_request_response` before the call occurs.
    """

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self.pull_request_response: GitHubResponse[PullRequest] = GitHubResponse[PullRequest](
            data=PullRequest(number=1, html_url='https://github.com/test/repo/pull/1'),
            headers={},
        )

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
        self._record(
            'create_pull_request',
            owner=owner,
            repo=repo,
            title=title,
            head=head,
            base=base,
            body=body,
            draft=draft,
        )
        return self.pull_request_response

    async def add_labels_to_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: list[str],
        timeout: float | None = None,
    ) -> GitHubResponse[None]:
        self._record('add_labels_to_issue', owner=owner, repo=repo, issue_number=issue_number, labels=labels)
        return GitHubResponse[None].model_validate({'data': None, 'headers': {}})

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

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _record(self, method: str, **kwargs: Any) -> None:
        self.requests.append(RecordedRequest(method=method, kwargs=kwargs))


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

    mocker.patch('ddev.utils.github_async.async_github_client', fake_context)
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': 'ghp_test'})
    return fake
