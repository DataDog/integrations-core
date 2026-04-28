# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.utils.fs import Path

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
    from datadog_checks.dev.tooling.commands.release.changelog import towncrier

    integrations: list[Integration] = []
    for target in targets:
        try:
            integrations.append(app.repo.integrations.get(target))
        except OSError as e:
            app.abort(str(e))

    rendered = [
        (
            integration.name,
            towncrier(
                str(integration.path), 'build', '--draft', '--version', 'Unreleased', return_output=True
            ).stdout.strip(),
        )
        for integration in integrations
    ]
    output = _format_output(rendered)

    if output_file:
        output_file.write_text(output, encoding='utf-8')
        app.display_success(f'Wrote changelog preview to {output_file}')
    else:
        app.display(output, markup=False)


def _format_output(rendered: list[tuple[str, str]]) -> str:
    if len(rendered) == 1:
        return rendered[0][1]
    return '\n\n'.join(f'# {name}\n\n{content}' for name, content in rendered)
