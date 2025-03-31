from typing import TYPE_CHECKING

import click
from rich.syntax import Syntax

from ddev.config.file import RootConfig, deep_merge_with_list_handling
from ddev.config.utils import scrub_config
from ddev.utils.fs import Path
from ddev.utils.toml import dumps_toml_data

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command()
@click.pass_obj
def local_repo(app: "Application"):
    """
    Creates a local .ddev.toml file in the current directory with a local repo configuration.
    """
    app.config_file.overrides_path = Path.cwd() / '.ddev.toml'
    local_repo_config = {
        'repos': {'local': str(app.config_file.overrides_path.resolve().parent)},
        'repo': 'local',
    }

    if app.config_file.overrides_path.exists():
        app.display_info('Local config file already exists. Updating...')
        local_config = app.config_file.overrides_model.raw_data
        config = deep_merge_with_list_handling(local_config, local_repo_config)
    else:
        config = local_repo_config

    app.config_file.overrides_model = RootConfig(config)
    app.config_file.update()

    app.display_success(f'Local repo configuration added in {app.config_file.pretty_overrides_path}')
    app.display('Local config content:')
    scrub_config(app.config_file.overrides_model.raw_data)
    app.output(
        Syntax(dumps_toml_data(app.config_file.overrides_model.raw_data).rstrip(), 'toml', background_color='default')
    )
