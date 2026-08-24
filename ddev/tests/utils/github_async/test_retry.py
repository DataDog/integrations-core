# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for retrying the failures that are not rate limiting.

The question every test here answers is which failures a given endpoint replays, and the reason it
matters is that replaying the wrong one duplicates a side effect: a second workflow run, a second
comment. Rate-limit retries are a different layer and live in ``test_rate_limiting.py``.
"""

from __future__ import annotations

import logging

import httpx
import pytest

from ddev.utils.github_async import AsyncGitHubClient
from ddev.utils.github_async.retry import (
    MUTATION_RETRY,
    NO_RETRY,
    SAFE_RETRY,
    RetryPolicies,
    RetryPolicy,
    never,
    on_status,
    on_transport_error,
)
from ddev.utils.github_errors import GitHubUnexpectedRedirectError
from tests.utils.github_async.helpers import ENDPOINT_CALLS, TOKEN, json_response, recording_transport
from tests.utils.github_async.payloads import (
    full_pull_request_payload,
    issue_comment_payload,
    workflow_job,
    workflow_run_payload,
)

pytestmark = pytest.mark.usefixtures("instant_backoff")

# A policy that would retry anything, to prove the client's exclusions win regardless.
RETRY_EVERYTHING = RetryPolicy(should_retry=lambda exc: True, attempts=3)


def policy_for(kind: str) -> RetryPolicy:
    return SAFE_RETRY if kind == "safe" else MUTATION_RETRY


# ---------------------------------------------------------------------------
# Per-endpoint defaults
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", ENDPOINT_CALLS, ids=lambda case: case.id)
async def test_a_server_error_is_replayed_only_where_replaying_is_safe(case) -> None:
    """A 503 says nothing about whether the request landed, so only replayable endpoints try again.

    Catches the mistake that matters most here: widening the default of a create endpoint, where a
    replay leaves a duplicate workflow run, comment or check run behind.
    """
    transport, calls = recording_transport([httpx.Response(503), case.ok_response()])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    if case.default_retry == "safe":
        await case.call(client)
        assert len(calls) == 2
    else:
        with pytest.raises(httpx.HTTPStatusError):
            await case.call(client)
        assert len(calls) == 1


@pytest.mark.parametrize("case", ENDPOINT_CALLS, ids=lambda case: case.id)
async def test_a_request_that_never_left_is_replayed_by_every_endpoint(case) -> None:
    """A refused connection proves GitHub never saw the request, so even a create can safely repeat.

    Without this, a mutating endpoint would give up on a blip that cost it nothing.
    """
    transport, calls = recording_transport([httpx.ConnectError("refused")])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(httpx.ConnectError):
        await case.call(client)

    assert len(calls) == policy_for(case.default_retry).attempts


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(httpx.ReadTimeout("timed out"), id="read_timeout"),
        pytest.param(httpx.RemoteProtocolError("disconnected"), id="server_disconnected"),
    ],
)
async def test_a_mutation_does_not_replay_a_request_that_may_have_landed(error: Exception) -> None:
    """Once the request is on the wire, a failure cannot tell us whether GitHub acted on it.

    A dispatch replayed in that state starts a second batch of test jobs, so this is the case where
    giving up is the cheaper mistake.
    """
    transport, calls = recording_transport([error])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(type(error)):
        await client.create_workflow_dispatch("o", "r", "wf.yml", "main")

    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Caller overrides
# ---------------------------------------------------------------------------


async def test_a_caller_can_turn_retrying_off_for_one_call() -> None:
    transport, calls = recording_transport([httpx.Response(503), json_response(workflow_run_payload())])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_workflow_run("o", "r", 42, retry=NO_RETRY)

    assert len(calls) == 1


async def test_a_caller_can_widen_a_mutation_that_it_knows_is_safe_to_repeat() -> None:
    """The default is deliberately cautious, so a caller that can absorb a duplicate may opt in."""
    transport, calls = recording_transport([httpx.Response(503), json_response(issue_comment_payload())])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    await client.create_issue_comment("o", "r", 1, "body", retry=SAFE_RETRY)

    assert len(calls) == 2


async def test_the_client_defaults_can_be_replaced_wholesale() -> None:
    """Dispatcher builds these from config, so the constructor argument has to reach the requests."""
    transport, calls = recording_transport([httpx.ConnectError("refused")])
    policies = RetryPolicies(safe=SAFE_RETRY.replace(attempts=5), mutating=MUTATION_RETRY)
    client = AsyncGitHubClient(token=TOKEN, transport=transport, retry_policies=policies)

    with pytest.raises(httpx.ConnectError):
        await client.get_workflow_run("o", "r", 42)

    assert len(calls) == 5


# ---------------------------------------------------------------------------
# What no policy may retry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx.Response(401), id="unauthenticated"),
        pytest.param(httpx.Response(403), id="permission_denied"),
        pytest.param(httpx.Response(403, headers={"retry-after": "5", "x-ratelimit-remaining": "0"}), id="rate_limit"),
        pytest.param(httpx.Response(302, headers={"location": "https://elsewhere.example"}), id="redirect"),
    ],
)
async def test_the_client_refuses_to_replay_what_replaying_cannot_fix(response: httpx.Response) -> None:
    """Even asked to retry everything, these stay single attempts.

    Credentials do not improve by asking again, a rate-limit response belongs to the limiter whose
    pause is the correct wait, and a redirect is an answer rather than a failure. A policy that could
    opt into these would turn each one into a slower version of the same outcome.
    """
    transport, calls = recording_transport([response])
    client = AsyncGitHubClient(token=TOKEN, transport=transport, max_rate_limit_retries=0)

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_workflow_run("o", "r", 42, retry=RETRY_EVERYTHING)

    assert len(calls) == 1


async def test_a_missing_resource_is_an_answer_rather_than_a_failure_to_retry() -> None:
    """``get_pull_request`` returning 404 means there is no pull request for that number.

    Dispatcher relies on that answer to fall through to commit resolution, so retrying it would only
    delay a decision GitHub has already given. It stays out of the defaults rather than out of every
    policy, since a caller waiting for a freshly created resource to appear may opt in.
    """
    transport, calls = recording_transport(
        [httpx.Response(404), httpx.Response(404), json_response(full_pull_request_payload(number=5))]
    )
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_pull_request("o", "r", 5)

    assert len(calls) == 1

    # The same 404, with a caller that is waiting for the resource to appear: retried, then found.
    await client.get_pull_request("o", "r", 5, retry=SAFE_RETRY.also_on(on_status(404)))
    assert len(calls) == 3


# ---------------------------------------------------------------------------
# Redirects
# ---------------------------------------------------------------------------


async def test_an_unexpected_redirect_names_the_endpoint_and_is_not_followed() -> None:
    """Following a redirect would send the token to whoever the Location names.

    The client never follows one, so the risk is a caller misreading the generic HTTP error that used
    to surface and "fixing" it by enabling redirects.
    """
    transport, calls = recording_transport([httpx.Response(302, headers={"location": "https://evil.example/steal"})])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(GitHubUnexpectedRedirectError) as exc_info:
        await client.get_workflow_run("o", "r", 42)

    message = str(exc_info.value)
    assert "/repos/o/r/actions/runs/42" in message
    assert "https://evil.example/steal" in message
    assert len(calls) == 1
    assert calls[0].url.host == "api.github.com"


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


async def test_a_failing_page_is_retried_without_refetching_the_pages_already_read() -> None:
    """Pagination is a sequence of requests, so a blip on page two must not restart page one."""
    page_one = json_response(
        {"total_count": 2, "jobs": [workflow_job(1)]},
        headers={"link": '<https://api.github.com/next>; rel="next"'},
    )
    page_two = json_response({"total_count": 2, "jobs": [workflow_job(2)]})
    transport, calls = recording_transport([page_one, httpx.Response(503), page_two])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    pages = [page async for page in client.list_workflow_jobs("o", "r", 42)]

    assert len(calls) == 3
    assert [job.id for page in pages for job in page.data.jobs] == [1, 2]


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


async def test_a_retry_is_reported_with_its_cause(caplog: pytest.LogCaptureFixture) -> None:
    """A silent retry hides a degraded GitHub behind a slow run, so the cause has to reach the log."""
    transport, _ = recording_transport([httpx.Response(503), json_response(workflow_run_payload())])
    logger = logging.getLogger("test-github-client")
    client = AsyncGitHubClient(token=TOKEN, transport=transport, logger=logger)

    with caplog.at_level(logging.WARNING, logger="test-github-client"):
        await client.get_workflow_run("o", "r", 42)

    records = [record for record in caplog.records if record.name == "test-github-client"]
    assert len(records) == 1
    assert "/repos/o/r/actions/runs/42" in records[0].getMessage()
    assert "503" in records[0].getMessage()
    assert records[0].attempt == 2


# ---------------------------------------------------------------------------
# Composing policies
# ---------------------------------------------------------------------------


def test_also_on_keeps_what_the_policy_already_retried() -> None:
    """The point of composing is starting from a default, so widening must not drop its conditions."""
    policy = SAFE_RETRY.also_on(on_status(404))

    assert policy.should_retry(_status_error(404))
    assert policy.should_retry(_status_error(503))
    assert policy.should_retry(httpx.ConnectError("refused"))


def test_unless_removes_a_condition_the_policy_would_otherwise_retry() -> None:
    policy = SAFE_RETRY.unless(on_status(503))

    assert not policy.should_retry(_status_error(503))
    assert policy.should_retry(_status_error(502))


def test_a_policy_that_cannot_retry_is_rejected_rather_than_silently_useless() -> None:
    """``attempts=0`` would make every request fail without being sent."""
    with pytest.raises(ValueError, match="attempts must be at least 1"):
        RetryPolicy(should_retry=on_transport_error, attempts=0)


def test_no_retry_refuses_everything() -> None:
    assert NO_RETRY.should_retry is never
    assert NO_RETRY.attempts == 1


def _status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.github.com/x")
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=request, response=httpx.Response(status_code, request=request)
    )
