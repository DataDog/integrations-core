# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""`ddev release test-agent` — dispatch the Linux + Windows Agent test workflows.

The orchestration body lives here so the file reads top-to-bottom as the command's story.
Each step delegates to a sibling module (`validation`, `images`, `dispatch`), and every
helper module is imported lazily inside the function body so `ddev --help` only pays for
`click` from this package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


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
    from ddev.cli.release.test_agent.dispatch import dispatch_both
    from ddev.cli.release.test_agent.images import build_image_refs, resolve_version, validate_images_exist
    from ddev.cli.release.test_agent.validation import (
        Branch,
        fetch_target,
        validate_input,
        verify_workflows_present_on_ref,
    )

    target = validate_input(app, branch, tag)

    if not app.config.github.token:
        app.abort('GitHub token required. Set `github.token` via `ddev config set github.token <token>`.')

    fetch_target(app, target)
    verify_workflows_present_on_ref(app, target)

    version = resolve_version(app, target)
    validate_images_exist(app, version)
    linux_image, windows_image = build_image_refs(version)

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
    is_branch = isinstance(target, Branch)
    _print_plan(app, ref=target.name, version=version, is_branch=is_branch, inputs=inputs)

    if dry_run:
        app.display_info('Dry run — no workflows dispatched.')
        return

    if not yes and not click.confirm('Dispatch both workflows?', default=False):
        app.abort('Aborted by user.')

    try:
        linux_url, windows_url = dispatch_both(app.config.github.token, ref=target.name, inputs=inputs)
    except RuntimeError as e:
        app.abort(str(e))
    else:
        _print_result(app, linux_url=linux_url, windows_url=windows_url)


def _print_plan(
    app: Application,
    *,
    ref: str,
    version: str,
    is_branch: bool,
    inputs: dict[str, str],
) -> None:
    """Render the resolved dispatch plan via the stderr-bound `display_info` channel.

    All progress lines (`display_waiting`/`display_success`) default to stderr; keeping the
    plan on the same channel means piping the command into a file leaves stdout clean and
    keeps the whole pre-dispatch narrative coherent on stderr.
    """
    from ddev.cli.release.test_agent.dispatch import WORKFLOW_LINUX, WORKFLOW_WINDOWS

    app.display_info('Dispatch plan')
    app.display_info(f'  Workflows: {WORKFLOW_LINUX}, {WORKFLOW_WINDOWS}')
    app.display_info(f'  Ref: {ref}')
    if is_branch:
        app.display_info(f'  Resolved RC: {version}')
    for key, value in inputs.items():
        app.display_info(f'  {key}: {value}')


def _print_result(app: Application, *, linux_url: str, windows_url: str) -> None:
    app.display_success('Workflows dispatched.')
    app.display_pair('Linux', linux_url)
    app.display_pair('Windows', windows_url)
