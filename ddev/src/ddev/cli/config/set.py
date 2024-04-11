# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click


@click.command('set', short_help='Assign values to config file entries')
@click.argument('key')
@click.argument('value', required=False)
@click.pass_obj
def set_value(app, key, value):
    """
    Assign values to config file entries. If the value is omitted,
    you will be prompted, with the input hidden if it is sensitive.
    """
    from fnmatch import fnmatch

    import tomlkit

    from ddev.config.model import ConfigurationError, RootConfig
    from ddev.config.utils import SCRUBBED_GLOBS, create_toml_document, save_toml_document, scrub_config

    scrubbing = any(fnmatch(key, glob) for glob in SCRUBBED_GLOBS)
    if value is None:
        value = click.prompt(f'Value for `{key}`', hide_input=scrubbing)

    if (fnmatch(key, 'repos.*') or fnmatch(key, 'repos.*.path')) and not value.startswith('~'):
        value = os.path.abspath(value)

    user_config = new_config = tomlkit.parse(app.config_file.read())

    data = [value]
    data.extend(reversed(key.split('.')))
    key = data.pop()
    value = data.pop()

    # Use a separate mapping to show only what has changed in the end
    branch_config_root = branch_config = {}

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

    try:
        RootConfig(user_config).parse_fields()
    except ConfigurationError as e:
        app.display_error(str(e))
        app.abort()

    save_toml_document(user_config, app.config_file.path)
    if scrubbing:
        scrub_config(branch_config_root)

    rendered_changed = tomlkit.dumps(create_toml_document(branch_config_root)).rstrip()

    from rich.syntax import Syntax

    app.display_success('New setting:')
    app.output(Syntax(rendered_changed, 'toml', background_color='default'))
