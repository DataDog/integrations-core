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
    from collections.abc import Sequence

    from ddev.cli.application import Application
    from ddev.cli.release.test_agent.dispatch import DispatchedWorkflow


@click.command('test-agent', short_help='Dispatch the Agent test workflows against a branch or tag')
@click.option('--branch', help='Release branch to test, e.g. `7.80.x`.')
@click.option('--tag', help='Agent release tag to test, e.g. `7.80.0-rc.1` or `7.80.0`.')
@click.option('--dry-run', is_flag=True, help='Resolve images and print the plan without dispatching.')
@click.option('--monitor', is_flag=True, help='Monitor dispatched workflow jobs until both workflows finish.')
@click.option(
    '--poll-interval',
    type=click.FloatRange(min=1.0),
    default=10.0,
    show_default=True,
    help='Seconds between workflow monitor polls.',
)
@click.option('--yes', '-y', is_flag=True, help='Skip the interactive confirmation prompt.')
@click.pass_obj
def test_agent(
    app: Application,
    branch: str | None,
    tag: str | None,
    dry_run: bool,
    monitor: bool,
    poll_interval: float,
    yes: bool,
) -> None:
    """Trigger `test-agent.yml` and `test-agent-windows.yml` against the resolved Agent image.

    Exactly one of `--branch` or `--tag` must be provided. When `--branch` is given, the latest
    `MAJ.MIN.0-rc.N` published to `registry.datadoghq.com/agent` is used as the Agent image.
    When `--tag` is given, that exact tag is used. Linux and Windows (servercore) variants are
    both validated against the registry before either workflow is dispatched.
    """
    import logging

    from ddev.cli.release.test_agent.dispatch import dispatch_both
    from ddev.cli.release.test_agent.images import build_image_refs, resolve_version, validate_images_exist
    from ddev.cli.release.test_agent.validation import (
        Branch,
        fetch_target,
        validate_input,
        verify_workflows_present_on_ref,
    )

    logging.getLogger('httpx').setLevel(logging.WARNING)

    target = validate_input(app, branch, tag)

    if not app.config.github.token:
        app.abort('GitHub token required. Set `github.token` via `ddev config set github.token <token>`.')

    fetch_target(app, target)
    verify_workflows_present_on_ref(app, target)
    app.display_info('')

    version = resolve_version(app, target)
    app.display_info('')

    validate_images_exist(app, version)
    linux_image, windows_image = build_image_refs(version)
    app.display_info('')

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
    app.display_info('')

    if dry_run:
        app.display_info('Dry run — no workflows dispatched.')
        return

    if not yes and not click.confirm('Dispatch both workflows?', default=False):
        app.abort('Aborted by user.')

    try:
        workflows = dispatch_both(app.config.github.token, ref=target.name, inputs=inputs)
    except RuntimeError as e:
        app.abort(str(e))
    else:
        if not monitor:
            app.display_info('')
            _print_result(app, workflows=workflows)

    if monitor:
        from ddev.cli.release.test_agent.monitoring import monitor_dispatched_workflows

        try:
            monitor_dispatched_workflows(
                app,
                app.config.github.token,
                ref=target.name,
                workflows=workflows,
                poll_interval=poll_interval,
            )
        except RuntimeError as e:
            app.abort(f'Failed to monitor workflows: {e}')


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
    from rich.panel import Panel

    from ddev.cli.release.test_agent.validation import WORKFLOW_LINUX, WORKFLOW_WINDOWS

    rows: list[tuple[str, str]] = [
        ('Workflows', f'{WORKFLOW_LINUX}, {WORKFLOW_WINDOWS}'),
        ('Ref', ref),
    ]
    if is_branch:
        rows.append(('Resolved RC', version))
    rows.extend(inputs.items())

    app.output(
        Panel(app.labeled_lines(rows), title='Dispatch plan', title_align='left', border_style='cyan'), stderr=True
    )


def _print_result(app: Application, *, workflows: Sequence[DispatchedWorkflow]) -> None:
    """Render the two run URLs in a rich Panel, matching the look of `ddev release port-commit`."""
    from rich.panel import Panel

    rows = [(workflow.label, workflow.html_url) for workflow in workflows]
    app.output(
        Panel(app.labeled_lines(rows), title='Workflows dispatched', title_align='left', border_style='cyan'),
        stderr=True,
    )
