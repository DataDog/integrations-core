# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""`ddev release test-agent` — dispatch the Linux + Windows Agent test workflows."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

BRANCH_PATTERN = r'^\d+\.\d+\.x$'
TAG_PATTERN = r'^\d+\.\d+\.\d+(-rc\.\d+)?$'

WORKFLOW_LINUX = 'test-agent.yml'
WORKFLOW_WINDOWS = 'test-agent-windows.yml'
WORKFLOW_FILES = [
    f'.github/workflows/{WORKFLOW_LINUX}',
    f'.github/workflows/{WORKFLOW_WINDOWS}',
]

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

    inputs = {
        'test-py3': True,
        'test-py2': False,
        'agent-image': linux_image,
        'agent-image-windows': windows_image,
    }
    _print_plan(app, ref=ref, version=version, branch=branch, linux_image=linux_image, windows_image=windows_image)

    if dry_run:
        app.display_info('Dry run — no workflows dispatched.')
        return

    if not yes and not click.confirm('Dispatch both workflows?', default=False):
        app.abort('Aborted by user.')

    try:
        linux_url, windows_url = _dispatch_both(app, ref=ref, inputs=inputs)
    except RuntimeError as e:
        app.abort(str(e))
    _print_result(app, ref=ref, linux_url=linux_url, windows_url=windows_url)


def _validate_input(app: Application, branch: str | None, tag: str | None) -> tuple[str | None, str | None]:
    """Normalize and validate inputs, returning (branch, tag) with at most one set."""
    if bool(branch) == bool(tag):
        app.abort('Exactly one of --branch or --tag must be provided.')

    if branch is not None and not re.match(BRANCH_PATTERN, branch):
        app.abort(f'Invalid branch: {branch!r}. Must match {BRANCH_PATTERN}.')

    if tag is not None:
        normalized = tag.lstrip('v')
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
                f'Image `{image}` not found in registry.datadoghq.com. '
                'Confirm the Agent release has been published.'
            )


def _print_plan(
    app: Application,
    *,
    ref: str,
    version: str,
    branch: str | None,
    linux_image: str,
    windows_image: str,
) -> None:
    app.display_header('Dispatch plan')
    app.display_pair('Workflows', f'{WORKFLOW_LINUX}, {WORKFLOW_WINDOWS}')
    app.display_pair('Ref', ref)
    if branch is not None:
        app.display_pair('Resolved RC', version)
    app.display_pair('Linux image', linux_image)
    app.display_pair('Windows image', windows_image)
    app.display_pair('test-py3', 'true')
    app.display_pair('test-py2', 'false')


def _print_result(app: Application, *, ref: str, linux_url: str, windows_url: str) -> None:
    app.display_success('Workflows dispatched.')
    app.display_pair('Linux', linux_url)
    app.display_pair('Windows', windows_url)


def _dispatch_both(app: Application, *, ref: str, inputs: dict[str, object]) -> tuple[str, str]:
    """Dispatch both workflows in parallel via the async GitHub client. Returns (linux_url, windows_url)."""
    import asyncio

    owner = REPO_OWNER
    repo = app.repo.full_name
    token = app.config.github.token

    return asyncio.run(_dispatch_both_async(token, owner, repo, ref, inputs))


async def _dispatch_both_async(
    token: str,
    owner: str,
    repo: str,
    ref: str,
    inputs: dict[str, object],
) -> tuple[str, str]:
    import asyncio

    from ddev.utils.github_async import async_github_client

    async with async_github_client(token=token) as client:
        results = await asyncio.gather(
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

    return _extract_run_urls(owner, repo, ref, results)


def _extract_run_urls(owner: str, repo: str, ref: str, results: list[object]) -> tuple[str, str]:
    """Pull html_urls out of two gather results, raising on any exception with a partial-success hint."""
    linux_result, windows_result = results

    def url_or_raise(result: object, sibling_url: str | None, label: str) -> str:
        if isinstance(result, BaseException):
            if sibling_url is not None:
                raise RuntimeError(
                    f'{label} dispatch failed: {result}. The other workflow was dispatched at {sibling_url}.'
                ) from result
            raise RuntimeError(f'{label} dispatch failed: {result}') from result
        return result.data.html_url  # type: ignore[union-attr,attr-defined]

    linux_url_or_none = None if isinstance(linux_result, BaseException) else linux_result.data.html_url  # type: ignore[union-attr,attr-defined]
    windows_url_or_none = None if isinstance(windows_result, BaseException) else windows_result.data.html_url  # type: ignore[union-attr,attr-defined]

    linux_url = url_or_raise(linux_result, windows_url_or_none, 'Linux')
    windows_url = url_or_raise(windows_result, linux_url_or_none, 'Windows')
    return linux_url, windows_url
