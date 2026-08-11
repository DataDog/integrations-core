"""Tests for the github_async response models: parsing contracts, no transport or client."""

from __future__ import annotations

import pytest

from ddev.utils.github_async.models import (
    GitHubUser,
    Label,
    PullRequest,
    PullRequestRef,
    PullRequestState,
)
from tests.utils.github_async.payloads import full_pull_request_payload


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
