# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""`ddev release test-agent` — dispatch the Linux + Windows Agent test workflows."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.application import Application
    from ddev.utils.github_async import GitHubResponse
    from ddev.utils.github_async.models import WorkflowDispatchResult

    DispatchOutcome = GitHubResponse[WorkflowDispatchResult] | BaseException

BRANCH_PATTERN = r'^\d+\.\d+\.x$'
TAG_PATTERN = r'^\d+\.\d+\.\d+(-rc\.\d+)?$'

WORKFLOW_LINUX = 'test-agent.yml'
WORKFLOW_WINDOWS = 'test-agent-windows.yml'
WORKFLOW_FILES = [
    f'.github/workflows/{WORKFLOW_LINUX}',
    f'.github/workflows/{WORKFLOW_WINDOWS}',
]

# Hard-coded: the two test workflows only live on DataDog/integrations-core. Forks have nothing
# to dispatch even if the branch/tag exists, so deferring this to repo metadata would just hide
# misconfiguration. If we ever ship the workflows elsewhere, plumb the owner through here.
REPO_OWNER = 'DataDog'


@click.command('test-agent', short_help='Dispatch the Agent test workflows against a branch or tag')
@click.option('--branch', help='Release branch to test, e.g. `7.80.x`.')
@click.option('--tag', help='Agent release tag to test, e.g. `7.80.0-rc.1` or `7.80.0`.')
@click.option('--dry-run', is_flag=True, help='Resolve images and print the plan without dispatching.')
@click.option('--yes', '-y', is_flag=True, help='Skip the interactive confirmation prompt.')
@click.pass_obj
def test_agent(app: Application, branch: str | None, tag: str | None, dry_run: bool, yes: bool) -> None:
    """Trigger `test-agent.yml` and `test-agent-windows.yml` against the resolved Agent image.

    Exactly one of `--branch` or `--tag` must be provided. When `--branch` is given, the latest
    `MAJ.MIN.0-rc.N` published to `registry.datadoghq.com/agent` is used as the Agent image.
    When `--tag` is given, that exact tag is used. Linux and Windows (servercore) variants are
    both validated against the registry before either workflow is dispatched.
    """
    branch, tag = _validate_input(app, branch, tag)
    ref = branch or tag
    assert ref is not None

    _verify_ref_exists(app, branch=branch, tag=tag)
    _verify_workflows_present_on_ref(app, ref)

    version = _resolve_version(app, branch=branch, tag=tag)
    linux_image, windows_image = _build_image_refs(version)
    _validate_images_exist(app, linux_image, windows_image)

    # GitHub's workflow_dispatch API expects every value in `inputs` to be a string, even for
    # `type: boolean` workflow inputs — booleans are parsed from the lowercase string form.
    inputs: dict[str, str] = {
        'test-py3': 'true',
        'test-py2': 'false',
        'agent-image': linux_image,
        'agent-image-windows': windows_image,
    }
    _print_plan(app, ref=ref, version=version, branch=branch, inputs=inputs)

    if dry_run:
        app.display_info('Dry run — no workflows dispatched.')
        return

    if not yes and not click.confirm('Dispatch both workflows?', default=False):
        app.abort('Aborted by user.')

    try:
        linux_url, windows_url = _dispatch_both(app, ref=ref, inputs=inputs)
    except RuntimeError as e:
        cause = f' (caused by: {e.__cause__!r})' if e.__cause__ is not None else ''
        app.abort(f'{e}{cause}')
    _print_result(app, ref=ref, linux_url=linux_url, windows_url=windows_url)


def _validate_input(app: Application, branch: str | None, tag: str | None) -> tuple[str | None, str | None]:
    """Normalize and validate inputs, returning (branch, tag) with at most one set."""
    if bool(branch) == bool(tag):
        app.abort('Exactly one of --branch or --tag must be provided.')

    if branch is not None and not re.match(BRANCH_PATTERN, branch):
        app.abort(f'Invalid branch: {branch!r}. Must match {BRANCH_PATTERN}.')

    if tag is not None:
        normalized = tag.removeprefix('v')
        if not re.match(TAG_PATTERN, normalized):
            app.abort(f'Invalid tag: {tag!r}. Must match {TAG_PATTERN}.')
        tag = normalized

    return branch, tag


def _verify_ref_exists(app: Application, *, branch: str | None, tag: str | None) -> None:
    """Confirm the ref is published on origin via `git ls-remote`."""
    if branch is not None:
        kind, value, flag = 'branch', branch, '--heads'
    else:
        assert tag is not None
        kind, value, flag = 'tag', tag, '--tags'

    output = app.repo.git.capture('ls-remote', flag, 'origin', value)
    if not output.strip():
        app.abort(f'{kind.capitalize()} `{value}` not found on origin.')


def _verify_workflows_present_on_ref(app: Application, ref: str) -> None:
    """Confirm both workflow files exist at the target ref."""
    missing: list[str] = []
    for path in WORKFLOW_FILES:
        try:
            app.repo.git.show_file(path, ref)
        except OSError:
            missing.append(path)

    if missing:
        app.abort(
            f'Ref `{ref}` is missing required workflow file(s): {", ".join(missing)}. '
            'Pick a newer ref that includes both `test-agent.yml` and `test-agent-windows.yml`.'
        )


def _resolve_version(app: Application, *, branch: str | None, tag: str | None) -> str:
    """Pick the Agent image tag to test: the explicit tag, or the highest published RC for a branch."""
    if tag is not None:
        return tag

    assert branch is not None
    from ddev.cli.release.test_agent.registry import list_agent_rc_tags

    major_str, minor_str, _ = branch.split('.')
    major, minor = int(major_str), int(minor_str)

    app.display_waiting(f'Looking up latest {major}.{minor}.0-rc.* in registry.datadoghq.com...')
    tags = list_agent_rc_tags(major, minor)
    if not tags:
        app.abort(
            f'No `{major}.{minor}.0-rc.*` tags found in registry.datadoghq.com/agent. '
            'Pass --tag explicitly once the first RC is published.'
        )
    latest = tags[-1]
    app.display_success(f'Latest RC: {latest}')
    return latest


def _build_image_refs(version: str) -> tuple[str, str]:
    base = f'registry.datadoghq.com/agent:{version}'
    return base, f'{base}-servercore'


def _validate_images_exist(app: Application, linux_image: str, windows_image: str) -> None:
    from ddev.cli.release.test_agent.registry import manifest_exists

    for image in (linux_image, windows_image):
        tag = image.rsplit(':', 1)[1]
        app.display_waiting(f'Checking `{image}`...')
        if not manifest_exists(tag):
            app.abort(
                f'Image `{image}` not found in registry.datadoghq.com. Confirm the Agent release has been published.'
            )


def _print_plan(
    app: Application,
    *,
    ref: str,
    version: str,
    branch: str | None,
    inputs: dict[str, str],
) -> None:
    app.display_header('Dispatch plan')
    app.display_pair('Workflows', f'{WORKFLOW_LINUX}, {WORKFLOW_WINDOWS}')
    app.display_pair('Ref', ref)
    if branch is not None:
        app.display_pair('Resolved RC', version)
    for key, value in inputs.items():
        app.display_pair(key, value)


def _print_result(app: Application, *, ref: str, linux_url: str, windows_url: str) -> None:
    app.display_success('Workflows dispatched.')
    app.display_pair('Linux', linux_url)
    app.display_pair('Windows', windows_url)


def _dispatch_both(app: Application, *, ref: str, inputs: dict[str, object]) -> tuple[str, str]:
    """Dispatch both workflows in parallel via the async GitHub client. Returns (linux_url, windows_url)."""
    owner = REPO_OWNER
    repo = app.repo.full_name
    token = app.config.github.token

    results = asyncio.run(_dispatch_both_async(token, owner, repo, ref, inputs))
    return _extract_run_urls(results)


async def _dispatch_both_async(
    token: str,
    owner: str,
    repo: str,
    ref: str,
    inputs: dict[str, object],
) -> Sequence[DispatchOutcome]:
    from ddev.utils.github_async import async_github_client

    async with async_github_client(token=token) as client:
        return await asyncio.gather(
            client.create_workflow_dispatch(
                owner=owner,
                repo=repo,
                workflow_id=WORKFLOW_LINUX,
                ref=ref,
                inputs=inputs,
                return_run_details=True,
            ),
            client.create_workflow_dispatch(
                owner=owner,
                repo=repo,
                workflow_id=WORKFLOW_WINDOWS,
                ref=ref,
                inputs=inputs,
                return_run_details=True,
            ),
            return_exceptions=True,
        )


def _extract_run_urls(results: Sequence[DispatchOutcome]) -> tuple[str, str]:
    """Pull html_urls out of two gather results, raising on any exception with a partial-success hint."""
    linux_result, windows_result = results

    if isinstance(linux_result, BaseException):
        if isinstance(windows_result, BaseException):
            raise RuntimeError(
                f'Both dispatches failed. Linux: {linux_result}. Windows: {windows_result}.'
            ) from linux_result
        sibling = windows_result.data.html_url
        raise RuntimeError(
            f'Linux dispatch failed: {linux_result}. The other workflow was dispatched at {sibling}.'
        ) from linux_result

    if isinstance(windows_result, BaseException):
        sibling = linux_result.data.html_url
        raise RuntimeError(
            f'Windows dispatch failed: {windows_result}. The other workflow was dispatched at {sibling}.'
        ) from windows_result

    return linux_result.data.html_url, windows_result.data.html_url
