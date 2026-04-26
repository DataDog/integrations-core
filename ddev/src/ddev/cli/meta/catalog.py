# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.integration.core import Integration


@click.command(short_help='Catalog repository targets')
@click.argument('targets', nargs=-1, required=True, metavar='TARGETS')
@click.option('--json', 'json_output', is_flag=True, help='Output the catalog as JSON.')
@click.pass_context
@click.pass_obj
def catalog(app: Application, ctx: click.Context, targets: tuple[str, ...], *, json_output: bool) -> None:
    """Catalog repository targets."""
    from pydantic import BaseModel, TypeAdapter

    from ddev.integration.core import Integration
    from ddev.utils.fs import Path

    class TargetDescription(BaseModel):
        path: str
        is_integration: bool
        is_package: bool
        is_tile: bool
        is_testable: bool
        is_shippable: bool
        is_agent_check: bool
        is_jmx_check: bool
        has_metrics: bool

    def describe_integration(integration: Integration, target: str) -> TargetDescription:
        return TargetDescription(
            path=target,
            is_integration=integration.is_integration,
            is_package=integration.is_package,
            is_tile=integration.is_tile,
            is_testable=integration.is_testable,
            is_shippable=integration.is_shippable,
            is_agent_check=integration.is_agent_check,
            is_jmx_check=integration.is_jmx_check,
            has_metrics=integration.has_metrics,
        )

    def describe_target(target: str) -> TargetDescription:
        click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str).convert(target, None, ctx)
        path = Path(target).expand()
        if not path.is_absolute():
            path = Path.cwd() / path

        return describe_integration(Integration(path, app.repo.path, app.repo.config), str(Path(target)))

    if targets == ('all',):
        descriptions = [
            describe_integration(integration, integration.name) for integration in app.repo.integrations.iter(['all'])
        ]
    elif 'all' in targets:
        raise click.BadParameter('The `all` target cannot be combined with other targets.', param_hint='TARGETS')
    else:
        descriptions = [describe_target(target) for target in targets]

    if json_output:
        click.echo(TypeAdapter(list[TargetDescription]).dump_json(descriptions, indent=2).decode())
        return

    columns = {
        'Target': {i: description.path for i, description in enumerate(descriptions)},
        'Integration': {i: str(description.is_integration).lower() for i, description in enumerate(descriptions)},
        'Package': {i: str(description.is_package).lower() for i, description in enumerate(descriptions)},
        'Tile': {i: str(description.is_tile).lower() for i, description in enumerate(descriptions)},
        'Testable': {i: str(description.is_testable).lower() for i, description in enumerate(descriptions)},
        'Shippable': {i: str(description.is_shippable).lower() for i, description in enumerate(descriptions)},
        'Agent Check': {i: str(description.is_agent_check).lower() for i, description in enumerate(descriptions)},
        'JMX Check': {i: str(description.is_jmx_check).lower() for i, description in enumerate(descriptions)},
        'Metrics': {i: str(description.has_metrics).lower() for i, description in enumerate(descriptions)},
    }
    app.display_table('Targets', columns, show_lines=True)
