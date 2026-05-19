# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import click

from ddev.cli.validate.all.github import extract_pr_number

if TYPE_CHECKING:
    from ddev.cli.application import Application


REQUIRED_LABELS: frozenset[str] = frozenset({'qa/skip-qa', 'qa/required'})

HELP_MESSAGE = (
    "Every pull request must declare its QA expectation by setting exactly one of:\n"
    "  - 'qa/required'  if this PR ships changes that need to be validated during QA.\n"
    "  - 'qa/skip-qa'   if this PR does not need QA validation (e.g., docs, tests, "
    "developer tooling, or no agent-impacting changes).\n"
)


def _load_event_payload() -> dict | None:
    """Read and parse the GitHub Actions event payload.

    Returns `None` when the path is unset (callers treat this as a benign
    skip). Raises `OSError`/`json.JSONDecodeError` if the path is set but the
    file cannot be read or parsed, and `TypeError` if the payload parses to
    anything other than a JSON object. The caller turns each into an abort so
    every non-success exit goes through `app.abort` instead of bubbling as an
    uncaught exception.
    """
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path:
        return None
    with open(event_path, encoding='utf-8') as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise TypeError(f'GitHub event payload at {event_path} is not a JSON object.')
    return payload


def _is_fork_pr(app: Application, event: dict) -> bool:
    pr = event.get('pull_request') or {}
    head = pr.get('head') or {}
    head_repo = (head.get('repo') or {}).get('full_name')
    base = pr.get('base') or {}
    base_repo = os.environ.get('GITHUB_REPOSITORY') or (base.get('repo') or {}).get('full_name')
    if not head_repo or not base_repo:
        app.abort('pull_request event payload is missing head/base repo information.')
    return head_repo != base_repo


@click.command(short_help='Validate the QA decision label on the current pull request')
@click.pass_obj
def qa_label(app: Application):
    """Fail unless the current pull request has exactly one QA decision label.

    Skipped outside of pull_request events and on PRs from forks (the workflow
    has no token to read labels there).
    """
    if os.environ.get('GITHUB_EVENT_NAME') != 'pull_request':
        app.display_info('Not running in a pull_request context; skipping qa-label validation.')
        return

    try:
        event = _load_event_payload()
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        app.abort(f'Could not read GitHub event payload: {exc}')

    if event is None:
        app.display_info('GITHUB_EVENT_PATH is not set; skipping qa-label validation.')
        return

    if _is_fork_pr(app, event):
        app.display_info('Pull request is from a fork; skipping qa-label validation.')
        return

    pr_number = extract_pr_number(event)
    if pr_number is None:
        app.display_warning('Could not determine pull request number; skipping qa-label validation.')
        return

    labels = app.github.get_pull_request_labels(pr_number)
    if labels is None:
        app.abort(f'Could not fetch pull request #{pr_number} to read its labels.')

    qa_labels = sorted(set(labels) & REQUIRED_LABELS)

    if len(qa_labels) == 1:
        app.display_success(f'QA label set: {qa_labels[0]}')
        return

    if not qa_labels:
        app.display_error(f'No QA decision label set on PR #{pr_number}.')
    else:
        app.display_error(f'PR #{pr_number} has more than one QA decision label: {", ".join(qa_labels)}.')

    app.display_info(HELP_MESSAGE)
    app.abort()
