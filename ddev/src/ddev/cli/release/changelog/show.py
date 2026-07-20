# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ddev.cli.application import Application


@click.command(short_help="Show the changelog section for a target's version")
@click.argument('target')
@click.argument('version')
@click.option(
    '--file',
    '-f',
    'output_file',
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help='Write the extracted section to this file (overwrites if it exists) instead of stdout',
)
@click.pass_obj
def show(app: Application, target: str, version: str, output_file: Path | None):
    """
    Print the section of TARGET's CHANGELOG.md that corresponds to VERSION.

    The output is the markdown content between the ``## VERSION`` heading and the
    next ``## `` heading, with surrounding blank lines stripped. Useful for
    populating GitHub release notes from the just-built changelog.
    """
    try:
        integration = app.repo.integrations.get(target)
    except OSError:
        app.abort(f'Unknown target: {target}')

    changelog_path = integration.path / 'CHANGELOG.md'
    if not changelog_path.is_file():
        app.abort(f'Changelog not found: {changelog_path}')

    section = _extract_version_section(changelog_path, version)
    if section is None:
        app.abort(f'No changelog section found for {target} version {version}')

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(section, encoding='utf-8')
        app.display_success(f'Wrote changelog section for {target} {version} to {output_file}')
    else:
        app.display_markdown(section)


def _iter_version_section(path: Path, version: str) -> Iterator[str]:
    """Yield the lines of the requested version's section, lazily.

    Stops as soon as the next ``## `` heading after the section is encountered,
    so we never read past the requested release in a long changelog.
    """
    with path.open(mode='r', encoding='utf-8') as f:
        in_section = False
        for line in f:
            if line.startswith('## '):
                tokens = line[3:].split()
                if in_section:
                    return
                if tokens and tokens[0] == version:
                    in_section = True
                    continue
            if in_section:
                yield line


def _extract_version_section(path: Path, version: str) -> str | None:
    section = ''.join(_iter_version_section(path, version)).strip('\n')
    return section or None
