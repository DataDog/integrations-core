# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""`ddev release test-agent` — dispatch the Linux + Windows Agent test workflows."""

from __future__ import annotations

import asyncio
import contextlib
import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

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

# Hard-coded: the two test workflows only live on DataDog/integrations-core. Forks and other
# integrations repos (extras, marketplace) have nothing to dispatch even if the branch/tag exists,
# so deferring either component to repo metadata would just hide misconfiguration. If we ever
# ship the workflows elsewhere, plumb the target through here.
REPO_OWNER = 'DataDog'
REPO_NAME = 'integrations-core'

# git error fragments that mean "ref exists but file is not in that tree" — i.e. the workflow
# really isn't on this branch/tag, as opposed to the ref itself being unreachable locally.
GIT_FILE_MISSING_FRAGMENTS = (
    'exists on disk',
    'does not exist',
    'no such path',
)
GIT_REF_MISSING_FRAGMENTS = (
    'invalid object name',
    'unknown revision',
    'bad revision',
    'ambiguous argument',
)


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

    if not app.config.github.token:
        app.abort('GitHub token required. Set `github.token` via `ddev config set github.token <token>`.')

    _verify_ref_exists(app, branch=branch, tag=tag)
    _verify_workflows_present_on_ref(app, branch=branch, tag=tag)

    version = _resolve_version(app, branch=branch, tag=tag)
    _validate_images_exist(app, version)
    linux_image, windows_image = _build_image_refs(version)

    # GitHub's workflow_dispatch API expects every value in `inputs` to be a string, even for
    # `type: boolean` workflow inputs — booleans are parsed from the lowercase string form.
    # `test-py2='false'` is sent to both dispatches by design: this command is forward-looking
    # and tests Python 3 only, even on Windows (where `test-agent-windows.yml` defaults
    # `test-py2` to `true` for legacy reasons).
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
        linux_url, windows_url = _dispatch_both(app.config.github.token, ref=ref, inputs=inputs)
    except RuntimeError as e:
        app.abort(str(e))
    else:
        _print_result(app, linux_url=linux_url, windows_url=windows_url)


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


def _verify_workflows_present_on_ref(app: Application, *, branch: str | None, tag: str | None) -> None:
    """Confirm both workflow files exist at the target ref.

    `git show <ref>:<path>` only resolves against local refs, so a branch the user has not yet
    fetched will not be found under its bare name. For branches we read `origin/<branch>` to
    consult the remote-tracking ref; for tags we use the tag name directly. Either way, the
    git error text is inspected to distinguish "file missing from the tree" from "ref not
    local" so the abort message points at the real problem.
    """
    if branch is not None:
        local_ref = f'origin/{branch}'
        fetch_hint = f'Run `git fetch origin {branch}` and try again.'
    else:
        assert tag is not None
        local_ref = tag
        fetch_hint = f'Run `git fetch origin tag {tag}` and try again.'

    missing: list[str] = []
    for path in WORKFLOW_FILES:
        try:
            app.repo.git.show_file(path, local_ref)
        except OSError as e:
            msg = str(e).lower()
            if any(fragment in msg for fragment in GIT_FILE_MISSING_FRAGMENTS):
                missing.append(path)
            elif any(fragment in msg for fragment in GIT_REF_MISSING_FRAGMENTS):
                app.abort(f'Ref `{local_ref}` is not in your local clone. {fetch_hint} (git error: {e})')
            else:
                app.abort(f'Failed to read `{path}` from `{local_ref}`: {e}')

    if missing:
        app.abort(
            f'Ref `{local_ref}` is missing required workflow file(s): {", ".join(missing)}. '
            'Pick a newer ref that includes both `test-agent.yml` and `test-agent-windows.yml`.'
        )


@contextlib.contextmanager
def _registry_errors(app: Application, target: str) -> Iterator[None]:
    """Translate any `httpx.HTTPError` raised inside the block into a clean `app.abort` message.

    `target` is interpolated into the abort text — e.g. `'tags'` for the tag listing or an
    image ref like `'registry.datadoghq.com/agent:7.80.0-rc.3'` for a manifest probe.
    """
    import httpx

    try:
        yield
    except httpx.HTTPError as e:
        app.abort(f'Failed to query registry.datadoghq.com for {target}: {e}')


def _resolve_version(app: Application, *, branch: str | None, tag: str | None) -> str:
    """Pick the Agent image tag to test: the explicit tag, or the highest published RC for a branch."""
    if tag is not None:
        return tag

    assert branch is not None
    from ddev.cli.release.test_agent.registry import list_agent_rc_tags

    major_str, minor_str, _ = branch.split('.')
    major, minor = int(major_str), int(minor_str)

    app.display_waiting(f'Looking up latest {major}.{minor}.0-rc.* in registry.datadoghq.com...')
    with _registry_errors(app, 'tags'):
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


def _validate_images_exist(app: Application, version: str) -> None:
    """Check that both the Linux (`<version>`) and Windows (`<version>-servercore`) manifests are published."""
    from ddev.cli.release.test_agent.registry import manifest_exists

    for tag in (version, f'{version}-servercore'):
        image = f'registry.datadoghq.com/agent:{tag}'
        app.display_waiting(f'Checking `{image}`...')
        with _registry_errors(app, f'`{image}`'):
            exists = manifest_exists(tag)
        if not exists:
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
    """Render the resolved dispatch plan via the stderr-bound `display_info` channel.

    All progress lines (`display_waiting`/`display_success`) default to stderr; keeping the
    plan on the same channel means piping the command into a file leaves stdout clean and
    keeps the whole pre-dispatch narrative coherent on stderr.
    """
    app.display_info('Dispatch plan')
    app.display_info(f'  Workflows: {WORKFLOW_LINUX}, {WORKFLOW_WINDOWS}')
    app.display_info(f'  Ref: {ref}')
    if branch is not None:
        app.display_info(f'  Resolved RC: {version}')
    for key, value in inputs.items():
        app.display_info(f'  {key}: {value}')


def _print_result(app: Application, *, linux_url: str, windows_url: str) -> None:
    app.display_success('Workflows dispatched.')
    app.display_pair('Linux', linux_url)
    app.display_pair('Windows', windows_url)


def _dispatch_both(token: str, *, ref: str, inputs: dict[str, str]) -> tuple[str, str]:
    """Dispatch both workflows in parallel via the async GitHub client. Returns (linux_url, windows_url)."""
    results = asyncio.run(_dispatch_both_async(token, REPO_OWNER, REPO_NAME, ref, inputs))
    return _extract_run_urls(results)


async def _dispatch_both_async(
    token: str,
    owner: str,
    repo: str,
    ref: str,
    inputs: dict[str, str],
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
    """Pull html_urls out of two gather results, raising on any exception with a partial-success hint.

    `asyncio.gather(return_exceptions=True)` captures `CancelledError`/`KeyboardInterrupt`
    (`BaseException` subclasses, not `Exception`) into its result list. Re-raise those first
    so flow-control exceptions propagate cleanly instead of being wrapped in `RuntimeError`.
    """
    linux_result, windows_result = results

    for result in (linux_result, windows_result):
        if isinstance(result, BaseException) and not isinstance(result, Exception):
            raise result

    if isinstance(linux_result, BaseException):
        if isinstance(windows_result, BaseException):
            raise RuntimeError(
                f'Both dispatches failed. Linux: {linux_result!r}. Windows: {windows_result!r}.'
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
