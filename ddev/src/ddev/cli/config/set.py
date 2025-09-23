# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import click

from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.application import Application


def config_file_to_read(app: Application, overrides: bool) -> Path:
    # If the overrides file exists, we will read from it
    from ddev.config.file import DDEV_TOML

    if overrides and app.config_file.overrides_available():
        config_to_read = app.config_file.overrides_path
    elif overrides:
        # If the overrides file does not exist, we will create it
        app.config_file.overrides_path = config_to_read = Path.cwd() / DDEV_TOML
        should_create = click.confirm("No overrides file found, would you like to create one in the current directory?")
        if should_create:
            app.config_file.overrides_path.write_text("")
        else:
            app.abort(
                "No overrides file found and no permission to create one. "
                "Run `ddev config set` to set values in the global config file."
            )
    else:
        config_to_read = app.config_file.global_path

    return config_to_read


def validate_final_config(app: Application, overrides: bool, config: dict[str, Any]):
    # If we are setting values on the overrides file, we need to merge with the global file
    # for validation
    from ddev.config.file import deep_merge_with_list_handling
    from ddev.config.model import ConfigurationError, RootConfig

    if overrides:
        config = deep_merge_with_list_handling(cast(RootConfig, app.config_file.combined_model).raw_data, config)
    try:
        RootConfig(config).parse_fields()
    except ConfigurationError as e:
        app.display_error(str(e))
        app.abort()


@click.command('set', short_help='Assign values to config file entries')
@click.argument('key')
@click.argument('value', required=False)
@click.option('--overrides', is_flag=True, help='Set the value in the local config file (.ddev.toml)')
@click.pass_obj
def set_value(app: Application, key: str, value: str | None, overrides: bool):
    """
    Assign values to config file entries. If the value is omitted,
    you will be prompted, with the input hidden if it is sensitive.
    """
    import os
    from fnmatch import fnmatch

    import tomlkit

    from ddev.config.utils import SCRUBBED_GLOBS, create_toml_document, save_toml_document, scrub_config

    scrubbing = any(fnmatch(key, glob) for glob in SCRUBBED_GLOBS)
    if value is None:
        value = cast(str, click.prompt(f'Value for `{key}`', hide_input=scrubbing))

    if (fnmatch(key, 'repos.*') or fnmatch(key, 'repos.*.path')) and not value.startswith('~'):
        value = os.path.abspath(value)

    config_to_read = config_file_to_read(app, overrides)
    user_config = new_config = tomlkit.parse(config_to_read.read_text())

    data = [value]
    data.extend(reversed(key.split('.')))
    key = data.pop()
    value = data.pop()

    # Use a separate mapping to show only what has changed in the end
    branch_config_root: dict[str, Any] = {}
    branch_config: dict[str, Any] = branch_config_root

    # Consider dots as keys
    while data:
        default_branch = {value: ''}
        branch_config[key] = default_branch
        branch_config = branch_config[key]

        new_value = new_config.get(key)
        if not hasattr(new_value, 'get'):
            new_value = default_branch

        new_config[key] = new_value
        new_config = new_config[key]

        key = value
        value = data.pop()

    if value.startswith(('{', '[')):
        from ast import literal_eval

        value = literal_eval(value)

    branch_config[key] = new_config[key] = value

    # https://github.com/sdispater/tomlkit/issues/48
    if new_config.__class__.__name__ == 'Table':  # no cov
        table_body = getattr(new_config.value, 'body', [])
        possible_whitespace = table_body[-2:]
        if len(possible_whitespace) == 2:
            for key, item in possible_whitespace:
                if key is not None:
                    break
                if item.__class__.__name__ != 'Whitespace':
                    break
            else:
                del table_body[-2]

    validate_final_config(app, overrides, user_config)

    save_toml_document(user_config, config_to_read)
    if scrubbing:
        scrub_config(branch_config_root)

    rendered_changed = tomlkit.dumps(create_toml_document(branch_config_root)).rstrip()

    from rich.syntax import Syntax

    app.display_success('New setting:')
    app.output(Syntax(rendered_changed, 'toml', background_color='default'))
