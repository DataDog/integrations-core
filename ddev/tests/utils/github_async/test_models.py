"""Tests for the github_async response models: parsing contracts, no transport or client."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ddev.utils.github_async.models import (
    GitHubUser,
    Label,
    PullRequest,
    PullRequestRef,
    PullRequestState,
    WorkflowRun,
    WorkflowRunsList,
)
from tests.utils.github_async.payloads import full_pull_request_payload, workflow_run_payload


def test_pull_request_parses_full_response() -> None:
    """PullRequest parses its sub-models (GitHubUser, Label, PullRequestRef) end-to-end."""
    pr = PullRequest.model_validate(full_pull_request_payload(number=42))

    assert pr.id == 9042
    assert pr.number == 42
    assert pr.state is PullRequestState.OPEN
    assert pr.draft is True
    assert pr.title == "Fix bug"

    assert isinstance(pr.user, GitHubUser)
    assert pr.user.login == "octocat"

    assert [label.name for label in pr.labels] == ["qa/skip-qa", "backport/7.62.x"]
    assert all(isinstance(label, Label) for label in pr.labels)

    assert isinstance(pr.head, PullRequestRef)
    assert pr.head.ref == "alice/fix"
    assert pr.head.sha == "1234567890abcdef00"
    assert isinstance(pr.base, PullRequestRef)
    assert pr.base.ref == "master"

    assert [reviewer.login for reviewer in pr.requested_reviewers] == ["reviewer"]
    assert pr.created_at == "2026-05-01T00:00:00Z"


def test_pull_request_ignores_extra_fields() -> None:
    """Unknown top-level fields in the response must not break parsing."""
    payload = full_pull_request_payload(mergeable_state="clean", additions=42, unknown_future_field={"nested": True})
    pr = PullRequest.model_validate(payload)
    assert pr.number == 42


def test_workflow_run_parses_ordering_fields() -> None:
    """`run_number` and `head_sha` are required by the schema; `run_attempt` is optional."""
    run = WorkflowRun.model_validate(workflow_run_payload(head_sha="cafebabe", run_number=12, run_attempt=3))

    assert run.head_sha == "cafebabe"
    assert run.run_number == 12
    assert run.run_attempt == 3

    without_attempt = WorkflowRun.model_validate(workflow_run_payload())
    assert without_attempt.run_attempt is None


@pytest.mark.parametrize("missing", ["head_sha", "run_number"], ids=["head_sha", "run_number"])
def test_workflow_run_rejects_missing_required_ordering_field(missing: str) -> None:
    payload = workflow_run_payload()
    del payload[missing]

    with pytest.raises(ValidationError, match=missing):
        WorkflowRun.model_validate(payload)


def test_workflow_runs_list_parses_its_items() -> None:
    runs_list = WorkflowRunsList.model_validate(
        {"total_count": 2, "workflow_runs": [workflow_run_payload(id=1), workflow_run_payload(id=2)]}
    )

    assert runs_list.total_count == 2
    assert [run.id for run in runs_list.workflow_runs] == [1, 2]
    assert all(isinstance(run, WorkflowRun) for run in runs_list.workflow_runs)


def test_models_subpackage_unknown_attribute_raises_attribute_error() -> None:
    import ddev.utils.github_async.models as models

    with pytest.raises(AttributeError, match="no attribute"):
        models.NotARealModel  # noqa: B018


def test_models_subpackage_loads_only_requested_submodule() -> None:
    """Importing one model must not eagerly load every other model submodule.

    Runs in a clean subprocess so the import effect is observable (the parent test process
    has already loaded everything for other tests).
    """
    import subprocess
    import sys
    import textwrap

    script = textwrap.dedent(
        """
        import sys
        from ddev.utils.github_async.models import PullRequest  # noqa: F401

        assert 'ddev.utils.github_async.client' not in sys.modules, 'client module should not be loaded'
        assert 'httpx' not in sys.modules, 'httpx should not be loaded when only models are imported'

        prefix = 'ddev.utils.github_async.models.'
        loaded = sorted(name[len(prefix):] for name in sys.modules if name.startswith(prefix))
        print(','.join(loaded))
        """
    )
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, check=True)
    loaded = set(result.stdout.strip().split(','))

    assert {'pull_request', 'user', 'label'} <= loaded
    assert 'workflow' not in loaded
    assert 'comment' not in loaded
