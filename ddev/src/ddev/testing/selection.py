# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.integration.core import Integration
    from ddev.utils.hatch import Environment


class TestCommand(click.Command):
    """Keep migration guidance consistent across both test commands for callers using legacy syntax."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except click.UsageError as error:
            error.message += (
                f'\nUse explicit test options, for example: {ctx.command_path} postgres '
                '--envs default --pytest-args=\'-m "not flaky"\''
            )
            raise


def parse_envs(ctx: click.Context, param: click.Parameter, value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    entries = [entry.strip() for entry in value.split(',')]
    if not all(entries):
        raise click.BadParameter('Environment entries must not be empty.', ctx=ctx, param=param)
    return tuple(dict.fromkeys(entries))


def parse_pytest_args(ctx: click.Context, param: click.Parameter, value: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(value, posix=True))
    except ValueError as error:
        raise click.BadParameter(str(error), ctx=ctx, param=param) from error


def validate_target(target: str, command: str) -> None:
    if ':' in target:
        name, _, envs = target.partition(':')
        raise click.UsageError(
            f'Colon environment selectors are not supported. Use: {command} {name} '
            f'--envs {shlex.quote(envs or "default")} --pytest-args=\'-m "not flaky"\''
        )


def e2e_pytest_args(args: Sequence[str]) -> tuple[str, ...]:
    forwarded: list[str] = []
    markers: list[str] = []
    iterator = iter(args)
    for arg in iterator:
        if arg == '--':
            forwarded.extend((arg, *iterator))
            break
        if arg == '-m':
            try:
                markers.append(next(iterator))
            except StopIteration as error:
                raise click.UsageError('The pytest -m option requires a marker expression.') from error
        elif arg.startswith('-m') and len(arg) > 2:
            markers.append(arg[2:].removeprefix('='))
        else:
            forwarded.append(arg)
    expression = ' and '.join([*(f'({marker})' for marker in markers), 'e2e'])
    return ('-m', expression, *forwarded)


@dataclass
class EnvironmentCatalog:
    environments: dict[str, Environment]
    aliases: dict[str, list[str]]

    def resolve(self, selectors: Sequence[str]) -> list[str]:
        unknown = [name for name in selectors if name not in self.environments and name not in self.aliases]
        if unknown:
            raise click.UsageError(f'Unknown environments: {", ".join(unknown)}. Use `ddev test --list` to list names.')
        return list(dict.fromkeys(name for selector in selectors for name in self.aliases.get(selector, [selector])))

    def select(
        self, names: Sequence[str], *, mode: str, platform: str, python_filter: str | None = None
    ) -> tuple[list[str], dict[str, str]]:
        selected = []
        excluded = {}
        for name in names:
            environment = self.environments[name]
            if not getattr(environment, mode):
                excluded[name] = f'{mode.replace("_", "-")} option'
            elif environment.platforms and platform not in environment.platforms:
                excluded[name] = f'platform {platform}'
            elif python_filter and environment.python != python_filter:
                excluded[name] = f'Python filter {python_filter}'
            else:
                selected.append(name)
        return selected, excluded


def load_environment_catalog(integration: Integration) -> EnvironmentCatalog:
    # Project's declared path type is Hatch's Path, not ddev's pathlib subclass.
    from hatch.project.core import Project
    from hatch.utils.fs import Path

    from ddev.utils.hatch import Environment

    # Hatch owns matrix expansion, inheritance and collector configuration.
    selection_fields = ('type', 'python', 'platforms', 'test-env', 'e2e-env', 'benchmark-env', 'latest-env')
    try:
        config = Project(Path(str(integration.path))).config
        return EnvironmentCatalog(
            {
                name: Environment(name=name, **{key: data[key] for key in selection_fields if key in data})
                for name, data in config.envs.items()
            },
            {name: list(data['envs']) for name, data in config.matrices.items()},
        )
    except (TypeError, ValueError) as error:
        raise click.ClickException(f'Failed to load environments for {integration.name}: {error}') from error
