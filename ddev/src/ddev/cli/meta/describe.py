# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Describe repository targets')
@click.argument(
    'targets',
    nargs=-1,
    required=True,
    metavar='TARGETS',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str),
)
@click.option('--json', 'json_output', is_flag=True, help='Output the descriptions as JSON.')
@click.pass_obj
def describe(app: Application, targets: tuple[str, ...], *, json_output: bool) -> None:
    """Describe repository targets."""
    from pydantic import BaseModel, TypeAdapter

    from ddev.integration.core import Integration
    from ddev.utils.fs import Path

    class TargetDescription(BaseModel):
        path: str
        is_integration: bool

    def describe_target(target: str) -> TargetDescription:
        path = Path(target).expand()
        if not path.is_absolute():
            path = Path.cwd() / path

        integration = Integration(path, app.repo.path, app.repo.config)
        return TargetDescription(path=str(Path(target)), is_integration=integration.is_integration)

    descriptions = [describe_target(target) for target in targets]

    if json_output:
        click.echo(TypeAdapter(list[TargetDescription]).dump_json(descriptions, indent=2).decode())
        return

    columns = {
        'Target': {i: description.path for i, description in enumerate(descriptions)},
        'Is Integration': {i: str(description.is_integration).lower() for i, description in enumerate(descriptions)},
    }
    app.display_table('Targets', columns, show_lines=True)
