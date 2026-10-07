# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING

import click
from pydantic import ValidationError

from ddev.utils.github_actions import PullRequestEvent

if TYPE_CHECKING:
    from ddev.cli.application import Application


MAX_DESCRIPTION_LENGTH = 3000
# PRs opened before the checklist template existed are exempt. Set to the merge date of the template change.
ENFORCED_SINCE = datetime.fromisoformat('2026-10-02T00:00:00+00:00')
CHECKLIST_HEADING = 'Checklist before requesting review'
HEADING_PATTERN = re.compile(r'^##[ \t]+(.+?)[ \t]*$', re.MULTILINE)
COMMENT_PATTERN = re.compile(r'<!--.*?-->', re.DOTALL)
CHECKBOX_PATTERN = re.compile(r'^[ \t]*-[ \t]*\[([ \txX])\][ \t]*(.+?)[ \t]*$', re.MULTILINE)
RELEASE_TITLE_PATTERN = re.compile(
    r'^(?:\[backport\]\s*)?(?:\[release\]\s*|finalize agent release\b|release new integrations\b)',
    re.IGNORECASE,
)


def _sections(body: str) -> dict[str, str]:
    headings = list(HEADING_PATTERN.finditer(body))
    sections = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        sections[heading.group(1).strip()] = body[heading.end() : end]
    return sections


def _skip_reason(author: str, author_type: str, title: str, created_at: str | None) -> str | None:
    if created_at and datetime.fromisoformat(created_at.replace('Z', '+00:00')) < ENFORCED_SINCE:
        return f'PR opened before {ENFORCED_SINCE:%Y-%m-%d}, when the checklist template was introduced'
    if author_type == 'Bot':
        return f'bot author {author}'
    if RELEASE_TITLE_PATTERN.match(title):
        return 'release PR'
    return None


def _checklist(body: str) -> dict[str, bool]:
    """Map each checklist item's text to whether it is ticked, ignoring HTML comments."""
    section = _sections(COMMENT_PATTERN.sub('', body)).get(CHECKLIST_HEADING, '')
    return {' '.join(text.split()): bool(mark.strip()) for mark, text in CHECKBOX_PATTERN.findall(section)}


def _fetch_current_body(app: Application, repository: str, pr_number: int) -> str | None:
    """Return the PR's current description ('' if empty), or None if it could not be fetched."""
    import asyncio

    import httpx

    from ddev.utils.github_async import async_github_client
    from ddev.utils.github_errors import GitHubAuthenticationError

    owner, _, repo = repository.partition('/')
    token = app.config.github.token
    if not (owner and repo and token):
        return None

    async def fetch() -> str:
        async with async_github_client(token=token) as client:
            response = await client.get_pull_request(owner, repo, pr_number)
            return response.data.body or ''

    try:
        return asyncio.run(fetch())
    except GitHubAuthenticationError as error:
        app.abort(str(error))
    except httpx.HTTPError:
        return None


def _check_pr_description(body: str, required_items: list[str]) -> list[str]:
    visible_body = COMMENT_PATTERN.sub('', body)
    items = _checklist(body)
    errors = []
    for item in required_items:
        if item not in items:
            errors.append(f'Missing checklist item (restore it from the template): {item}')
        elif not items[item]:
            errors.append(f'Unchecked checklist item: {item}')

    description_length = len(visible_body)
    if description_length > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f'PR description is {description_length} characters; maximum is {MAX_DESCRIPTION_LENGTH}. '
            'Trim the description before requesting review.'
        )

    return errors


@click.command(short_help='Validate the current pull request description')
@click.option(
    '--event-name',
    envvar='GITHUB_EVENT_NAME',
    default='',
    help='GitHub event name; the validation only runs for `pull_request`. Defaults to $GITHUB_EVENT_NAME.',
)
@click.option(
    '--event-path',
    envvar='GITHUB_EVENT_PATH',
    default='',
    help='Path to the GitHub event payload JSON. Defaults to $GITHUB_EVENT_PATH.',
)
@click.pass_obj
def pr_description(app: Application, event_name: str, event_path: str):
    """Fail when the PR checklist is incomplete or the description is too long."""
    if event_name != 'pull_request':
        app.display_info('Not running in a pull_request context; skipping pr-description validation.')
        return

    if not event_path:
        app.display_info('No GitHub event payload path given; skipping pr-description validation.')
        return

    try:
        event = PullRequestEvent.load(event_path)
    except (OSError, json.JSONDecodeError, ValueError, ValidationError) as exc:
        app.abort(f'Could not read GitHub event payload: {exc}')

    pull_request = event.pull_request
    if pull_request is None:
        app.display_info('Event payload has no pull request; skipping pr-description validation.')
        return

    user = pull_request.user
    author = (user.login if user else None) or ''
    author_type = (user.type if user else None) or ''
    reason = _skip_reason(author, author_type, pull_request.title or '', pull_request.created_at)
    if reason:
        app.display_info(f'Skipping PR description check: {reason}.', markup=False)
        return

    template_path = app.repo.path / '.github' / 'PULL_REQUEST_TEMPLATE.md'
    try:
        template = template_path.read_text(encoding='utf-8')
    except OSError:
        app.display_info(f'No checklist items found because {template_path} could not be read; skipping validation.')
        return

    required_items = list(_checklist(template))
    if not required_items:
        app.display_info(
            f'No checklist items found under ## {CHECKLIST_HEADING} in {template_path}; skipping validation.'
        )
        return

    # Re-runs reuse the original event payload, so read the current description from the API.
    repository = event.base_repo
    body = _fetch_current_body(app, repository, pull_request.number) if repository and pull_request.number else None
    if body is None:
        app.display_warning('Could not fetch the current PR description; using the event payload, which may be stale.')
        body = pull_request.body or ''

    errors = _check_pr_description(body, required_items)
    if errors:
        for error in errors:
            app.display_error(error, markup=False)
        app.display_info('Update the pull request body using .github/PULL_REQUEST_TEMPLATE.md.')
        app.abort()

    app.display_success('PR description check passed.')
