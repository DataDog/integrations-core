# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, overload

from pydantic import BaseModel, Field, RootModel, model_validator

if TYPE_CHECKING:
    from collections.abc import Collection
    from typing import Any, Literal

    from ddev.integration.core import Integration

    from .platform import Platform


class HatchCommandError(Exception):
    pass


class Environment(BaseModel):
    """Represents a single environment configuration."""

    name: str
    type: str
    dependencies: list[str] = Field(default_factory=list)
    test_env: bool = Field(alias='test-env')
    e2e_env: bool = Field(alias='e2e-env')
    benchmark_env: bool = Field(alias='benchmark-env')
    latest_env: bool = Field(alias='latest-env')
    python: str | None = None
    scripts: dict[str, list[str]] = Field(default_factory=dict)
    platforms: list[str] = Field(default_factory=list)
    pre_install_commands: list[str] = Field(default_factory=list, alias='pre-install-commands')
    post_install_commands: list[str] = Field(default_factory=list, alias='post-install-commands')
    skip_install: bool = Field(False, alias='skip-install')


class HatchEnvironmentConfiguration(RootModel[list[Environment]]):
    """
    A root model that parses the top-level dictionary returned by the `hatch env show --json` command
    into a list of Environment models.
    """

    @model_validator(mode='before')
    @classmethod
    def transform_dict_to_list_with_name(cls, data: object) -> object:
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return [Environment(**value, name=key) for key, value in data.items()]

        raise ValueError(f'Invalid data type: {type(data)}. Expected a list or a dictionary.')


class EnvironmentFilter(Protocol):
    def __call__(self, environment: Environment) -> bool: ...


@overload
def env_show(platform: Platform, integration: Integration, as_json: Literal[True]) -> dict[str, Any]: ...


@overload
def env_show(platform: Platform, integration: Integration) -> dict[str, Any]: ...


@overload
def env_show(platform: Platform, integration: Integration, as_json: Literal[False]) -> str: ...


def env_show(platform: Platform, integration: Integration, as_json: bool = True) -> dict[str, Any] | str:
    import json
    import sys

    with integration.path.as_cwd():
        command = [sys.executable, '-m', 'hatch', '--no-color', '--no-interactive', 'env', 'show']
        if as_json:
            command.append('--json')

        env_data_output = platform.check_command_output(command)

        try:
            if as_json:
                return json.loads(env_data_output)
            return env_data_output
        except json.JSONDecodeError as error:
            raise HatchCommandError(
                f'Failed to parse environments for {integration.name!r}: {env_data_output!r}'
            ) from error


def list_environment_names(
    platform: Platform, integration: Integration, filters: Collection[EnvironmentFilter], match_all: bool = True
) -> list[str]:
    """
    List the names of the environments that match the given filters.

    If `match_all` is True, all filters must match. If False, any filter can match.
    """
    hatch_output = env_show(platform, integration)
    matching_rule = all if match_all else any

    return [
        env.name
        for env in HatchEnvironmentConfiguration.model_validate(hatch_output).root
        if matching_rule(filter(env) for filter in filters)
    ]


def get_hatch_env_vars(*, verbosity: int) -> dict[str, str]:
    env_vars = {}

    if verbosity > 0:
        env_vars['HATCH_VERBOSE'] = str(verbosity)
    elif verbosity < 0:
        env_vars['HATCH_QUIET'] = str(abs(verbosity))

    return env_vars
