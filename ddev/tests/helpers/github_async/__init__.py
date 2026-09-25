# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Test helpers for the async GitHub client.

Provides a `FakeAsyncGitHubClient` that records every call and lets tests
register canned responses with `mock_response`, plus one `make_<model>` factory
per API model with a realistic default for every field. The `fake_async_github`
pytest fixture that wires this fake into `async_github_client` lives in
the root `tests/conftest.py`.

Quick reference:

    def test_thing(fake_async_github):
        # Sticky default for all matching calls
        fake_async_github.mock_response(
            'create_pull_request',
            make_pull_request(number=5, changed_files=1),
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

from .factories import (
    DEFAULT_COMPLETED_AT,
    DEFAULT_DURATION_SECONDS,
    DEFAULT_STARTED_AT,
    make_artifact,
    make_artifacts_list,
    make_check_run,
    make_commit_info,
    make_file_commit,
    make_file_content,
    make_git_object,
    make_git_reference,
    make_github_user,
    make_issue_comment,
    make_job_step,
    make_label,
    make_pull_request,
    make_pull_request_file,
    make_pull_request_ref,
    make_pull_request_repo,
    make_pull_request_review_comment,
    make_pull_request_simple,
    make_response,
    make_workflow_dispatch_result,
    make_workflow_job,
    make_workflow_jobs_list,
    make_workflow_run,
)
from .fake_client import DEFAULT_COMMENT_ID, DEFAULT_DISPATCH_HTML_URL, FakeAsyncGitHubClient, RecordedRequest

__all__ = [
    'DEFAULT_COMMENT_ID',
    'DEFAULT_DISPATCH_HTML_URL',
    'DEFAULT_COMPLETED_AT',
    'DEFAULT_DURATION_SECONDS',
    'DEFAULT_STARTED_AT',
    'FakeAsyncGitHubClient',
    'RecordedRequest',
    'make_artifact',
    'make_artifacts_list',
    'make_check_run',
    'make_commit_info',
    'make_file_commit',
    'make_file_content',
    'make_git_object',
    'make_git_reference',
    'make_github_user',
    'make_issue_comment',
    'make_job_step',
    'make_label',
    'make_pull_request',
    'make_pull_request_file',
    'make_pull_request_ref',
    'make_pull_request_repo',
    'make_pull_request_review_comment',
    'make_pull_request_simple',
    'make_response',
    'make_workflow_dispatch_result',
    'make_workflow_job',
    'make_workflow_jobs_list',
    'make_workflow_run',
]
