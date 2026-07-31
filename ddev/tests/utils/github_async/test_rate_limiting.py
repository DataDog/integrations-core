"""Rate-limit wiring: snapshot parsing, governor observation, default construction, and retries."""

from __future__ import annotations

import dataclasses
import logging

import httpx
import pytest
from aiolimiter import AsyncLimiter

from ddev.utils.github_async import AsyncGitHubClient, async_github_client
from ddev.utils.github_async.client import github_rate_limit_snapshot
from ddev.utils.github_async.defaults import default_github_rate_limiter, log_rate_limit_events
from ddev.utils.github_async.models import WorkflowRun
from ddev.utils.github_errors import GitHubAuthenticationError
from ddev.utils.rate_limiting import (
    BucketEvent,
    BudgetGovernor,
    BudgetSnapshot,
    InstrumentedAsyncLimiter,
    PacingEvent,
    PacingReason,
    RateLimitEvent,
    SecondaryLimitEvent,
)
from tests.helpers.clock import FakeClock, advance_clock_on_sleep
from tests.utils.github_async.helpers import (
    TOKEN,
    governed_client,
    json_response,
    make_zip,
    patch_signed_download,
    recording_transport,
)
from tests.utils.github_async.payloads import workflow_run_payload

LOGGER_NAME = "ddev.utils.github_async.defaults"


async def test_client_request_with_rate_limiter_consumes_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(workflow_run_payload())

    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    events: list[RateLimitEvent] = []
    rate_limiter = InstrumentedAsyncLimiter(real_limiter, on_event=events.append)

    async with async_github_client(
        token=TOKEN, rate_limiter=rate_limiter, transport=httpx.MockTransport(handler)
    ) as client:
        result = await client.get_workflow_run("o", "r", 42)

    assert result.data.id == 42
    bucket_events = [event for event in events if isinstance(event, BucketEvent)]
    assert bucket_events == [BucketEvent(throttled=False, name="")]
    assert not real_limiter.has_capacity()


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        (
            {
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "4321",
                "x-ratelimit-reset": "1700000000",
                "retry-after": "30",
            },
            BudgetSnapshot(limit=5000, remaining=4321, reset_at=1700000000.0, retry_after=30.0),
        ),
        (
            {"x-ratelimit-limit": "5000", "x-ratelimit-remaining": "4999"},
            BudgetSnapshot(limit=5000, remaining=4999),
        ),
        ({"x-ratelimit-limit": "5000", "retry-after": "not-a-number"}, BudgetSnapshot(limit=5000)),
        ({"x-ratelimit-limit": "not-a-number"}, None),
        ({"content-type": "application/json"}, None),
    ],
    ids=["all_present", "partial_primary", "non_integer_retry_after", "all_unparseable", "no_ratelimit_headers"],
)
def test_github_rate_limit_snapshot(headers: dict[str, str], expected: BudgetSnapshot | None) -> None:
    assert github_rate_limit_snapshot(httpx.Headers(headers)) == expected


async def test_client_request_observes_rate_limit_headers_into_governor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            workflow_run_payload(),
            headers={"x-ratelimit-limit": "5000", "x-ratelimit-remaining": "4999", "x-ratelimit-reset": "1700000000"},
        )

    governor = BudgetGovernor()
    rate_limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), budget_governor=governor)

    async with async_github_client(
        token=TOKEN, rate_limiter=rate_limiter, transport=httpx.MockTransport(handler)
    ) as client:
        await client.get_workflow_run("o", "r", 42)

    assert governor.budget.limit == 5000
    assert governor.budget.remaining == 4999
    assert governor.budget.reset_at == 1700000000.0


async def test_default_rate_limiter_is_constructed_and_observes_403() -> None:
    """rate_limiter=None builds a limiter with a governor that observes a 403's retry-after."""
    transport, calls = recording_transport([httpx.Response(403, headers={"retry-after": "30"})])
    client = AsyncGitHubClient(token=TOKEN, transport=transport, max_rate_limit_retries=0)

    assert client._rate_limiter is not None
    governor = client._rate_limiter.budget_governor
    assert governor is not None

    with pytest.raises(httpx.HTTPStatusError):
        await client._request("GET", "/x")

    # The 403's retry-after was observed (before raise_for_status), arming the shared pause;
    # exact pause arithmetic is covered by the clocked governor tests.
    assert governor.pause_until > 0
    assert len(calls) == 1  # retries disabled: one call, no wait


async def test_retry_on_secondary_limit_returns_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 403 with retry-after then a 200 is retried once and the wait goes through the governor."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    events: list[RateLimitEvent] = []
    transport, calls = recording_transport([httpx.Response(403, headers={"retry-after": "5"}), httpx.Response(200)])
    client = governed_client(clock, transport, on_event=events.append)

    response = await client._request("GET", "/x")

    assert response.status_code == 200
    assert len(calls) == 2
    secondary_index = next(i for i, e in enumerate(events) if isinstance(e, SecondaryLimitEvent))
    pacing_index = next(
        i for i, e in enumerate(events) if isinstance(e, PacingEvent) and e.reason is PacingReason.SECONDARY_LIMIT
    )
    assert secondary_index < pacing_index


@pytest.mark.parametrize(
    "rate_limited_response",
    [
        pytest.param(
            httpx.Response(403, json={"message": "You have exceeded a secondary rate limit."}),
            id="response_message",
        ),
        pytest.param(httpx.Response(403, headers={"retry-after": "0"}), id="zero_retry_after"),
        pytest.param(httpx.Response(403, headers={"retry-after": "-1"}), id="negative_retry_after"),
    ],
)
async def test_retry_on_secondary_limit_without_valid_wait_returns_success(
    monkeypatch: pytest.MonkeyPatch, rate_limited_response: httpx.Response
) -> None:
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    events: list[RateLimitEvent] = []
    transport, calls = recording_transport([rate_limited_response, httpx.Response(200)])
    client = governed_client(clock, transport, on_event=events.append)

    response = await client._request("GET", "/x")

    assert response.status_code == 200
    assert len(calls) == 2
    assert any(isinstance(event, SecondaryLimitEvent) and event.retry_after_seconds == 60 for event in events)


async def test_retry_on_primary_exhaustion_waits_until_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 403 with x-ratelimit-remaining=0 is retried, and the retry waits until the window reset."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    events: list[RateLimitEvent] = []
    reset_at = clock.current + 30
    transport, calls = recording_transport(
        [
            httpx.Response(
                403,
                headers={"x-ratelimit-limit": "5000", "x-ratelimit-remaining": "0", "x-ratelimit-reset": str(reset_at)},
            ),
            httpx.Response(200),
        ]
    )
    client = governed_client(clock, transport, on_event=events.append)

    response = await client._request("GET", "/x")

    assert response.status_code == 200
    assert len(calls) == 2
    governor = client._rate_limiter.budget_governor
    assert clock.current == pytest.approx(reset_at + governor.buffer_seconds)
    assert any(isinstance(e, PacingEvent) and e.reason is PacingReason.EXHAUSTED for e in events)


@pytest.mark.parametrize("status_code", [401, 403])
async def test_authentication_error_is_actionable_and_not_retried(status_code: int) -> None:
    """Authentication failures are actionable and raise on the first attempt."""
    transport, calls = recording_transport([httpx.Response(status_code, headers={"x-ratelimit-remaining": "5"})])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(GitHubAuthenticationError) as exc_info:
        await client._request("GET", "/x")

    assert len(calls) == 1
    assert exc_info.value.response.status_code == status_code
    assert "ddev config set github.token" in str(exc_info.value)


async def test_no_retry_on_transport_error() -> None:
    """A transport error is never retried (the action may have executed); it propagates immediately."""
    transport, calls = recording_transport([httpx.ConnectError("boom")])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(httpx.ConnectError):
        await client._request("GET", "/x")

    assert len(calls) == 1


async def test_retries_exhausted_raises_after_max(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two consecutive rate-limit responses with max_rate_limit_retries=1 raise after exactly two calls."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    transport, calls = recording_transport(
        [httpx.Response(403, headers={"retry-after": "5"}), httpx.Response(403, headers={"retry-after": "5"})]
    )
    client = governed_client(clock, transport, max_rate_limit_retries=1)

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client._request("GET", "/x")

    assert len(calls) == 2
    assert type(exc_info.value) is httpx.HTTPStatusError


async def test_download_redirect_302_is_not_retried(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """The artifact 302 redirect is not a rate-limit response, so it resolves without any retry."""
    github_calls: list[httpx.Request] = []

    def github_handler(request: httpx.Request) -> httpx.Response:
        github_calls.append(request)
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=make_zip({"hello.txt": b"hi"}))

    patch_signed_download(monkeypatch, signed_handler)
    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))

    await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    assert len(github_calls) == 1


async def test_pagination_retries_only_the_rate_limited_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """A rate-limited page is retried in place; the iterator then continues to the next page."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    transport, calls = recording_transport(
        [
            httpx.Response(200, json={"page": 1}, headers={"link": '<https://api.github.com/next>; rel="next"'}),
            httpx.Response(403, headers={"retry-after": "5"}),
            httpx.Response(200, json={"page": 2}),
        ]
    )
    client = governed_client(clock, transport)

    pages = [response async for response in client._paginated_request("GET", "/start")]

    assert [page.status_code for page in pages] == [200, 200]
    assert len(calls) == 3  # page 1, page 2 (rate-limited), page 2 (retry)


async def test_endpoint_retries_rate_limit_then_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    """A public endpoint call retries a rate-limit response and returns the parsed model."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    transport, calls = recording_transport(
        [httpx.Response(403, headers={"retry-after": "5"}), json_response(workflow_run_payload())]
    )
    client = governed_client(clock, transport)

    result = await client.get_workflow_run("o", "r", 42)

    assert isinstance(result.data, WorkflowRun)
    assert result.data.id == 42
    assert len(calls) == 2


async def test_default_github_rate_limiter_wires_callback_into_both_slots() -> None:
    """The factory must wire the callback into both the bucket and the governor slots."""
    seen: list[RateLimitEvent] = []
    limiter = default_github_rate_limiter(on_event=seen.append)

    await limiter.__aenter__()  # bucket acquire -> BucketEvent (limiter slot)
    limiter.observe(BudgetSnapshot(limit=100, remaining=10, reset_at=2000.0))  # observe -> BudgetEvent (governor slot)

    kinds = {type(event).__name__ for event in seen}
    assert "BucketEvent" in kinds  # would be missing if the limiter slot were unwired
    assert "BudgetEvent" in kinds  # would be missing if the governor slot were unwired


@pytest.mark.parametrize(
    ("event", "expected_level"),
    [
        pytest.param(
            SecondaryLimitEvent(retry_after_seconds=5.0, pause_seconds=6.0), logging.WARNING, id="secondary_limit"
        ),
        pytest.param(PacingEvent(wait_seconds=0.0, reason=PacingReason.NONE), logging.DEBUG, id="healthy_pacing"),
        pytest.param(PacingEvent(wait_seconds=3.0, reason=PacingReason.RATIONING), logging.INFO, id="rationing"),
        pytest.param(PacingEvent(wait_seconds=9.0, reason=PacingReason.EXHAUSTED), logging.WARNING, id="exhausted"),
        pytest.param(PacingEvent(wait_seconds=9.0, reason=PacingReason.ABANDONED), logging.ERROR, id="abandoned"),
    ],
)
def test_log_rate_limit_events_level_mapping(
    caplog: pytest.LogCaptureFixture, event: RateLimitEvent, expected_level: int
) -> None:
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        log_rate_limit_events()(event)

    assert caplog.records
    assert caplog.records[-1].levelno == expected_level


def test_log_rate_limit_events_unknown_event_does_not_raise(caplog: pytest.LogCaptureFixture) -> None:
    """A future event type must fall through to the DEBUG catch-all, never raise."""

    @dataclasses.dataclass(frozen=True)
    class FutureEvent:
        type: str = "future"

    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        log_rate_limit_events()(FutureEvent())  # type: ignore[arg-type]

    assert caplog.records[-1].levelno == logging.DEBUG
