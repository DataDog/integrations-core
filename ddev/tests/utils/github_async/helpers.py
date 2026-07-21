"""Client-layer test helpers: transports, client factories, and the endpoint registry.

May import from payloads.py for response bodies, never the reverse. Pure payload factories that
model tests use live in payloads.py so they carry no client, httpx, or limiter dependency.
"""

from __future__ import annotations

import dataclasses
import io
import zipfile
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
from aiolimiter import AsyncLimiter

from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.rate_limiting import RATE_LIMIT_TIME_PERIOD, BudgetGovernor, InstrumentedAsyncLimiter
from tests.helpers.clock import FakeClock
from tests.utils.github_async.payloads import (
    artifact,
    check_run_payload,
    full_pull_request_payload,
    issue_comment_payload,
    pr_review_comment_payload,
    pull_request_payload,
    workflow_job,
    workflow_run_payload,
)

TOKEN = "ghp_test_token"


def json_response(data: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> httpx.Response:
    all_headers = {"content-type": "application/json"}
    if headers:
        all_headers.update(headers)
    return httpx.Response(status_code, json=data, headers=all_headers)


def make_client(handler: httpx.MockTransport | None = None) -> AsyncGitHubClient:
    transport = handler or httpx.MockTransport(lambda r: httpx.Response(200))
    return AsyncGitHubClient(token=TOKEN, transport=transport)


def make_zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def patch_signed_download(monkeypatch, handler: Any) -> None:
    """Route the anonymous signed-URL download through a mock transport."""
    real_async_client = httpx.AsyncClient

    def fake_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("ddev.utils.github_async.client.httpx.AsyncClient", fake_async_client)


def recording_transport(items: list[httpx.Response | Exception]) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """MockTransport that returns/raises *items* in order (last item repeats) and records each request."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        item = items[min(len(calls), len(items) - 1)]
        calls.append(request)
        if isinstance(item, Exception):
            raise item
        return item

    return httpx.MockTransport(handler), calls


def governed_client(
    clock: FakeClock,
    transport: httpx.MockTransport,
    on_event: Any = None,
    max_rate_limit_retries: int = 2,
) -> AsyncGitHubClient:
    """Client whose governor runs on *clock*, so retry waits are deterministic under a fake sleep."""
    governor = BudgetGovernor(now=clock, on_event=on_event)
    limiter = InstrumentedAsyncLimiter(
        AsyncLimiter(max_rate=5000, time_period=RATE_LIMIT_TIME_PERIOD),
        on_event=on_event,
        budget_governor=governor,
        name="github",
    )
    return AsyncGitHubClient(
        token=TOKEN, rate_limiter=limiter, transport=transport, max_rate_limit_retries=max_rate_limit_retries
    )


async def first_page(pages: AsyncIterator[GitHubResponse[Any]]) -> GitHubResponse[Any]:
    """Return the first page of a paginated endpoint (enough to exercise errors and headers)."""
    async for page in pages:
        return page
    raise AssertionError("expected at least one page")


@dataclasses.dataclass
class EndpointCase:
    id: str
    call: Callable[[AsyncGitHubClient], Awaitable[GitHubResponse[Any]]]
    ok_response: Callable[[], httpx.Response]


ENDPOINT_CALLS = [
    EndpointCase(
        "create_workflow_dispatch",
        lambda c: c.create_workflow_dispatch("o", "r", "wf.yml", "main", return_run_details=True),
        lambda: json_response(
            {"workflow_run_id": 1, "run_url": "https://api.github.com/x", "html_url": "https://github.com/x"}
        ),
    ),
    EndpointCase(
        "get_workflow_run", lambda c: c.get_workflow_run("o", "r", 42), lambda: json_response(workflow_run_payload())
    ),
    EndpointCase(
        "list_workflow_run_artifacts",
        lambda c: first_page(c.list_workflow_run_artifacts("o", "r", 1)),
        lambda: json_response({"total_count": 1, "artifacts": [artifact(1)]}),
    ),
    EndpointCase(
        "list_workflow_jobs",
        lambda c: first_page(c.list_workflow_jobs("o", "r", 42)),
        lambda: json_response({"total_count": 1, "jobs": [workflow_job(1)]}),
    ),
    EndpointCase(
        "create_issue_comment",
        lambda c: c.create_issue_comment("o", "r", 1, "body"),
        lambda: json_response(issue_comment_payload()),
    ),
    EndpointCase(
        "get_pull_request",
        lambda c: c.get_pull_request("o", "r", 5),
        lambda: json_response(full_pull_request_payload(number=5)),
    ),
    EndpointCase(
        "create_pull_request",
        lambda c: c.create_pull_request("o", "r", "t", "h", "b"),
        lambda: json_response(pull_request_payload(number=1), status_code=201),
    ),
    EndpointCase(
        "add_labels_to_issue",
        lambda c: c.add_labels_to_issue("o", "r", 1, ["bug"]),
        lambda: json_response([{"id": 1, "name": "bug"}]),
    ),
    EndpointCase(
        "create_pr_review_comment",
        lambda c: c.create_pr_review_comment("o", "r", 1, "body", "sha", "path", position=1),
        lambda: json_response(pr_review_comment_payload()),
    ),
    EndpointCase(
        "create_check_run",
        lambda c: c.create_check_run("o", "r", "ck", "abc", "in_progress"),
        lambda: json_response(check_run_payload()),
    ),
    EndpointCase(
        "update_check_run",
        lambda c: c.update_check_run("o", "r", 77, status="in_progress"),
        lambda: json_response(check_run_payload(id=77)),
    ),
]
