# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import click
from pydantic import BaseModel, TypeAdapter

from ddev.integration.core import Integration
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.application import Application

BOOL_FIELDS = (
    ('Integration', 'is_integration'),
    ('Package', 'is_package'),
    ('Tile', 'is_tile'),
    ('Testable', 'is_testable'),
    ('Shippable', 'is_shippable'),
    ('Agent Check', 'is_agent_check'),
    ('JMX Check', 'is_jmx_check'),
    ('Metrics', 'has_metrics'),
)

OutputFormat = Literal['terminal', 'json']


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


class TargetError(BaseModel):
    target: str
    error: str


class CatalogOutput(BaseModel):
    targets: list[TargetDescription]
    errors: list[TargetError]


def bool_str(value: bool) -> str:
    return 'true' if value else 'false'


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


def describe_target(app: Application, target: str) -> TargetDescription:
    path = Path(target).expand()
    if not path.is_dir():
        raise click.BadParameter(f"Directory '{target}' does not exist.", param_hint='TARGETS')

    if not path.is_absolute():
        path = Path.cwd() / path

    return describe_integration(Integration(path, app.repo.path, app.repo.config), path.name)


def target_error(target: str, error: Exception) -> TargetError:
    if isinstance(error, click.BadParameter):
        message = error.message
    else:
        message = str(error)

    return TargetError(target=target, error=message)


def catalog_target(app: Application, target: str) -> tuple[TargetDescription | None, TargetError | None]:
    try:
        return describe_target(app, target), None
    except Exception as e:
        return None, target_error(target, e)


def all_integrations(app: Application) -> CatalogOutput:
    descriptions: list[TargetDescription] = []
    errors: list[TargetError] = []
    for path in sorted(app.repo.path.iterdir()):
        if not path.is_dir() or path.name.startswith('.') or app.repo.git.is_worktree(path):
            continue

        integration = Integration(path, app.repo.path, app.repo.config)
        try:
            if integration.is_integration:
                descriptions.append(describe_integration(integration, integration.name))
        except Exception as e:
            errors.append(target_error(path.name, e))

    return CatalogOutput(targets=descriptions, errors=errors)


def get_table_columns(descriptions: list[TargetDescription]) -> dict[str, dict[int, str]]:
    columns: dict[str, dict[int, str]] = {
        'Target': {i: description.path for i, description in enumerate(descriptions)},
    }
    columns.update({title: {} for title, _ in BOOL_FIELDS})
    for i, description in enumerate(descriptions):
        for title, attr in BOOL_FIELDS:
            columns[title][i] = bool_str(getattr(description, attr))

    return columns


@click.command(short_help='Catalog repository targets')
@click.argument('targets', nargs=-1, required=True, metavar='TARGETS')
@click.option(
    '--format',
    'output_format',
    default='terminal',
    show_default=True,
    type=click.Choice(['terminal', 'json']),
    help='Output format.',
)
@click.option('-o', '--output', help='Write non-terminal output to a file.', type=click.Path(dir_okay=False))
@click.pass_context
@click.pass_obj
def catalog(
    app: Application, ctx: click.Context, targets: tuple[str, ...], *, output_format: OutputFormat, output: str | None
) -> None:
    """
    Catalog existing repository target directories.

    Use `all` by itself to catalog all integrations. Explicit targets can be
    any existing directories and are labeled by their basename in the output.
    """

    if output_format == 'terminal' and output:
        raise click.BadOptionUsage('output', '`--output` can only be used with non-terminal formats.')

    if targets == ('all',):
        catalog_output = all_integrations(app)
    elif 'all' in targets:
        raise click.BadParameter('The `all` target cannot be combined with other targets.', param_hint='TARGETS')
    else:
        descriptions = []
        errors = []
        for target in targets:
            description, error = catalog_target(app, target)
            if description is not None:
                descriptions.append(description)
            if error is not None:
                errors.append(error)

        catalog_output = CatalogOutput(targets=descriptions, errors=errors)

    if output_format == 'json':
        contents = TypeAdapter(CatalogOutput).dump_json(catalog_output, indent=2).decode()
        if output:
            Path(output).write_text(f'{contents}\n')
        else:
            click.echo(contents)

        if catalog_output.errors:
            ctx.exit(1)
        return

    app.display_table('Targets', get_table_columns(catalog_output.targets), show_lines=True)

    if catalog_output.errors:
        error_columns = {
            'Target': {i: error.target for i, error in enumerate(catalog_output.errors)},
            'Error': {i: error.error for i, error in enumerate(catalog_output.errors)},
        }
        app.display_table('Errors', error_columns, show_lines=True)
        ctx.exit(1)
