# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.repo.core import Integration


@click.command(short_help='Preview the generated changelog')
@click.argument('targets', nargs=-1, required=True)
@click.option(
    '--file',
    '-f',
    'output_file',
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help='Write the generated changelog to this file (overwrites if it exists) instead of stdout',
)
@click.pass_obj
def build(app: Application, targets: tuple[str, ...], output_file: Path | None):
    """
    Preview the changelog that would be generated from the entries in `changelog.d/`.

    Runs `towncrier build --draft` against each TARGET so the rendered output can be
    inspected without touching the integration's CHANGELOG.md or removing the news
    fragments.
    """
    config = app.repo.path / 'towncrier.toml'
    if not config.is_file():
        app.abort(f'Towncrier config not found at {config}')

    integrations: list[Integration] = []
    for target in targets:
        try:
            integrations.append(app.repo.integrations.get(target))
        except OSError as e:
            app.abort(str(e))

    rendered = [(integration.name, _render(config, integration.path)) for integration in integrations]
    output = _format_output(rendered)

    if output_file:
        output_file.write_text(output)
        app.display_success(f'Wrote changelog preview to {output_file}')
    else:
        click.echo(output)


def _render(config: Path, target_dir: Path) -> str:
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'towncrier',
            'build',
            '--draft',
            '--config',
            str(config),
            '--dir',
            str(target_dir),
            '--version',
            'Unreleased',
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = '\n'.join(part for part in (result.stderr.strip(), result.stdout.strip()) if part)
        raise click.ClickException(f'towncrier failed for {target_dir.name}:\n{details}')
    return result.stdout.strip()


def _format_output(rendered: list[tuple[str, str]]) -> str:
    if len(rendered) == 1:
        return rendered[0][1]
    return '\n\n'.join(f'# {name}\n\n{content}' for name, content in rendered)
