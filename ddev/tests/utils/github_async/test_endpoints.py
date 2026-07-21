"""Per-endpoint success tests plus the registry-driven cross-cutting error/header tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from pydantic import ValidationError

from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import (
    ArtifactsList,
    CheckRun,
    CheckRunConclusion,
    CheckRunStatus,
    GitHubUser,
    IssueComment,
    JobStep,
    JobStepStatus,
    Label,
    PullRequest,
    PullRequestReviewComment,
    PullRequestState,
    WorkflowDispatchResult,
    WorkflowJob,
    WorkflowJobConclusion,
    WorkflowJobsList,
    WorkflowJobStatus,
    WorkflowRun,
)
from tests.utils.github_async.helpers import ENDPOINT_CALLS, json_response, make_client
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

if TYPE_CHECKING:
    from tests.utils.github_async.helpers import EndpointCase


async def test_create_workflow_dispatch_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/actions/workflows/my-workflow.yml/dispatches" in request.url.path
        body = json.loads(request.content)
        assert body["ref"] == "main"
        assert body["return_run_details"] is True
        assert "inputs" not in body
        return json_response(
            {
                "workflow_run_id": 999,
                "run_url": "https://api.github.com/repos/owner/repo/actions/runs/999",
                "html_url": "https://github.com/owner/repo/actions/runs/999",
            },
            headers={"x-ratelimit-remaining": "59"},
        )

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_workflow_dispatch("owner", "repo", "my-workflow.yml", "main", return_run_details=True)
    assert isinstance(result, GitHubResponse)
    assert isinstance(result.data, WorkflowDispatchResult)
    assert result.data.workflow_run_id == 999
    assert result.headers.get("x-ratelimit-remaining") == "59"


async def test_create_workflow_dispatch_with_inputs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["inputs"] == {"env": "prod"}
        assert body["return_run_details"] is True
        return json_response(
            {
                "workflow_run_id": 1,
                "run_url": "https://api.github.com/repos/o/r/actions/runs/1",
                "html_url": "https://github.com/o/r/actions/runs/1",
            }
        )

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_workflow_dispatch(
        "o", "r", 123, "main", inputs={"env": "prod"}, return_run_details=True
    )
    assert result.data.workflow_run_id == 1


async def test_create_workflow_dispatch_omits_return_run_details_when_false() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "return_run_details" not in body
        return httpx.Response(204)

    client = make_client(httpx.MockTransport(handler))
    await client.create_workflow_dispatch("o", "r", "wf.yml", "main")


# ---------------------------------------------------------------------------
# get_workflow_run
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "is_completed"),
    [("completed", True), ("in_progress", False), ("queued", False)],
    ids=["completed", "in_progress", "queued"],
)
async def test_get_workflow_run_success(status: str, is_completed: bool) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/actions/runs/42" in request.url.path
        return json_response(workflow_run_payload(status=status))

    client = make_client(httpx.MockTransport(handler))
    result = await client.get_workflow_run("owner", "repo", 42)
    assert isinstance(result.data, WorkflowRun)
    assert result.data.id == 42
    assert result.data.status == status
    assert result.data.is_completed is is_completed


async def test_list_workflow_run_artifacts_single_page() -> None:
    artifacts = [artifact(1), artifact(2)]

    def handler(_: httpx.Request) -> httpx.Response:
        return json_response({"total_count": 2, "artifacts": artifacts})

    client = make_client(httpx.MockTransport(handler))
    pages = []
    async for page in client.list_workflow_run_artifacts("owner", "repo", 1):
        pages.append(page)

    assert len(pages) == 1
    assert isinstance(pages[0].data, ArtifactsList)
    assert pages[0].data.total_count == 2
    assert len(pages[0].data.artifacts) == 2


async def test_list_workflow_run_artifacts_per_page_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "100"
        return json_response({"total_count": 0, "artifacts": []})

    client = make_client(httpx.MockTransport(handler))
    async for _ in client.list_workflow_run_artifacts("owner", "repo", 1, per_page=100):
        pass


async def test_list_workflow_jobs_single_page() -> None:
    jobs = [workflow_job(1), workflow_job(2, status="in_progress", conclusion=None)]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/actions/runs/42/jobs" in request.url.path
        return json_response({"total_count": 2, "jobs": jobs})

    client = make_client(httpx.MockTransport(handler))
    pages = []
    async for page in client.list_workflow_jobs("owner", "repo", 42):
        pages.append(page)

    assert len(pages) == 1
    assert isinstance(pages[0].data, WorkflowJobsList)
    assert pages[0].data.total_count == 2

    first, second = pages[0].data.jobs
    assert isinstance(first, WorkflowJob)
    assert first.status is WorkflowJobStatus.COMPLETED
    assert first.conclusion is WorkflowJobConclusion.SUCCESS
    assert second.status is WorkflowJobStatus.IN_PROGRESS
    assert second.conclusion is None
    assert second.html_url == "https://github.com/owner/repo/actions/runs/42/job/2"

    # A step's status is its own StrEnum; its conclusion has no declared enum (stays str).
    step = first.steps[0]
    assert isinstance(step, JobStep)
    assert step.status is JobStepStatus.COMPLETED


async def test_list_workflow_jobs_unexpected_status_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"total_count": 1, "jobs": [workflow_job(1, status="bogus")]})

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(ValidationError):
        async for _ in client.list_workflow_jobs("owner", "repo", 42):
            pass


async def test_list_workflow_jobs_per_page_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "100"
        return json_response({"total_count": 0, "jobs": []})

    client = make_client(httpx.MockTransport(handler))
    async for _ in client.list_workflow_jobs("owner", "repo", 42, per_page=100):
        pass


async def test_create_issue_comment_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/issues/7/comments" in request.url.path
        body = json.loads(request.content)
        assert body["body"] == "LGTM"
        return json_response(issue_comment_payload(body="LGTM"), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_issue_comment("owner", "repo", 7, "LGTM")
    assert isinstance(result.data, IssueComment)
    assert result.data.body == "LGTM"
    assert isinstance(result.data.user, GitHubUser)
    assert result.data.user.login == "octocat"


async def test_create_pr_review_comment_success_with_position() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/pulls/3/comments" in request.url.path
        body = json.loads(request.content)
        assert body["commit_id"] == "abc123"
        assert body["path"] == "src/foo.py"
        assert body["position"] == 5
        assert "line" not in body
        return json_response(pr_review_comment_payload(), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pr_review_comment(
        "owner", "repo", 3, "Nice change", "abc123", "src/foo.py", position=5
    )
    assert isinstance(result.data, PullRequestReviewComment)
    assert result.data.commit_id == "abc123"
    assert isinstance(result.data.user, GitHubUser)
    assert result.data.user.login == "reviewer"


async def test_create_pr_review_comment_success_with_line_and_side() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["line"] == 10
        assert body["side"] == "RIGHT"
        assert "position" not in body
        return json_response(pr_review_comment_payload(), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pr_review_comment("o", "r", 1, "comment", "abc123", "file.py", line=10, side="RIGHT")
    assert isinstance(result.data, PullRequestReviewComment)


async def test_create_pull_request_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/repos/owner/repo/pulls" in request.url.path
        body = json.loads(request.content)
        assert body == {
            "title": "Fix bug",
            "head": "alice/fix",
            "base": "master",
            "body": "Fix description",
            "draft": False,
        }
        return json_response(pull_request_payload(number=42), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("owner", "repo", "Fix bug", "alice/fix", "master", "Fix description")
    assert isinstance(result.data, PullRequest)
    assert result.data.number == 42
    assert result.data.html_url == "https://github.com/owner/repo/pull/42"


async def test_create_pull_request_draft_true_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["draft"] is True
        return json_response(pull_request_payload(number=7), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("o", "r", "T", "h", "b", draft=True)
    assert result.data.number == 7


async def test_get_pull_request_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/repos/owner/repo/pulls/5" in request.url.path
        return json_response(full_pull_request_payload(number=5, state="open"))

    client = make_client(httpx.MockTransport(handler))
    result = await client.get_pull_request("owner", "repo", 5)
    assert isinstance(result.data, PullRequest)
    assert result.data.number == 5
    assert result.data.state is PullRequestState.OPEN


async def test_get_pull_request_unexpected_state_raises() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return json_response(full_pull_request_payload(number=5, state="merged"))

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(ValidationError):
        await client.get_pull_request("o", "r", 5)


async def test_list_pull_requests_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/repos/owner/repo/pulls"
        assert request.url.params.get("state") == "all"
        assert request.url.params.get("head") == "owner:alice/backport-123-to-7.62.x"
        return json_response(
            [
                full_pull_request_payload(number=5, state="closed", merged=True),
                full_pull_request_payload(number=6, state="closed", merged=True),
            ]
        )

    client = make_client(httpx.MockTransport(handler))
    result = await client.list_pull_requests("owner", "repo", state="all", head="owner:alice/backport-123-to-7.62.x")
    assert [pr.number for pr in result.data] == [5, 6]
    assert all(isinstance(pr, PullRequest) for pr in result.data)


async def test_list_pull_requests_empty_result() -> None:
    client = make_client(httpx.MockTransport(lambda r: json_response([])))
    result = await client.list_pull_requests("o", "r")
    assert result.data == []


async def test_list_pull_requests_defaults_to_open_and_omits_optional_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("state") == "open"
        assert "head" not in request.url.params
        assert "base" not in request.url.params
        return json_response([])

    client = make_client(httpx.MockTransport(handler))
    await client.list_pull_requests("o", "r")


async def test_list_pull_requests_forwards_base_filter() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("base") == "7.62.x"
        return json_response([pull_request_payload(number=1)])

    client = make_client(httpx.MockTransport(handler))
    result = await client.list_pull_requests("o", "r", base="7.62.x")
    assert result.data[0].number == 1


async def test_add_labels_to_issue_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/repos/owner/repo/issues/3/labels" in request.url.path
        body = json.loads(request.content)
        assert body == {"labels": ["qa/skip-qa", "backport/7.62.x"]}
        return json_response([{"id": 1, "name": "qa/skip-qa"}, {"id": 2, "name": "backport/7.62.x"}], status_code=200)

    client = make_client(httpx.MockTransport(handler))
    result = await client.add_labels_to_issue("owner", "repo", 3, ["qa/skip-qa", "backport/7.62.x"])
    assert [label.name for label in result.data] == ["qa/skip-qa", "backport/7.62.x"]
    assert all(isinstance(label, Label) for label in result.data)


async def test_create_check_run_success() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/repos/o/r/check-runs" in request.url.path
        captured.update(json.loads(request.content))
        return json_response(check_run_payload(name=captured["name"], head_sha=captured["head_sha"]))

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_check_run("o", "r", name="ck", head_sha="abc", status="in_progress")
    assert isinstance(result.data, CheckRun)
    assert result.data.id == 1
    assert result.data.status is CheckRunStatus.IN_PROGRESS
    assert captured == {"name": "ck", "head_sha": "abc", "status": "in_progress"}


async def test_create_check_run_with_optional_fields() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return json_response(check_run_payload())

    client = make_client(httpx.MockTransport(handler))
    await client.create_check_run(
        "o",
        "r",
        name="ck",
        head_sha="abc",
        status="in_progress",
        details_url="https://x",
        output={"title": "t", "summary": "s"},
    )
    assert captured["details_url"] == "https://x"
    assert captured["output"] == {"title": "t", "summary": "s"}


async def test_update_check_run_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert "/repos/o/r/check-runs/77" in request.url.path
        return json_response(check_run_payload(id=77, status="completed", conclusion="success"))

    client = make_client(httpx.MockTransport(handler))
    result = await client.update_check_run("o", "r", 77, status="completed", conclusion="success")
    assert result.data.status is CheckRunStatus.COMPLETED
    assert result.data.conclusion is CheckRunConclusion.SUCCESS


async def test_update_check_run_omits_unset_fields() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return json_response(check_run_payload(id=77))

    client = make_client(httpx.MockTransport(handler))
    await client.update_check_run("o", "r", 77, conclusion="failure")
    assert captured == {"conclusion": "failure"}


async def test_update_check_run_requires_conclusion_when_completed() -> None:
    requested = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requested
        requested = True
        return json_response(check_run_payload())

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="conclusion is required"):
        await client.update_check_run("o", "r", 77, status="completed")
    assert requested is False


async def test_update_check_run_unexpected_status_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(check_run_payload(id=77, status="bogus"))

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(ValidationError):
        await client.update_check_run("o", "r", 77, status="in_progress")


@pytest.mark.parametrize("case", ENDPOINT_CALLS, ids=[case.id for case in ENDPOINT_CALLS])
async def test_endpoint_http_error_raises(case: EndpointCase) -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await case.call(client)
    assert exc_info.value.response.status_code == 422


@pytest.mark.parametrize("case", ENDPOINT_CALLS, ids=[case.id for case in ENDPOINT_CALLS])
async def test_endpoint_forwards_response_headers(case: EndpointCase) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        response = case.ok_response()
        response.headers["x-ratelimit-remaining"] = "42"
        return response

    client = make_client(httpx.MockTransport(handler))
    result = await case.call(client)
    assert result.headers["x-ratelimit-remaining"] == "42"
