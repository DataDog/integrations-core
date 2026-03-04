# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.config.file import DDEV_TOML
from ddev.config.trust import trust_local_config
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Trust local secret command fields')
@click.pass_obj
def allow(app: Application):
    """Trust the current repo-local `.ddev.toml` file for command-based secret fields."""
    local_config_path = (
        app.config_file.overrides_path if app.config_file.overrides_available() else Path.cwd() / DDEV_TOML
    )

    if not local_config_path.is_file():
        app.display_info(f'No local config file found at `{local_config_path}`. Nothing to trust.')
        return

    already_trusted = trust_local_config(local_config_path)

    if already_trusted:
        app.display_success(f'Local config is already trusted: `{local_config_path}`')
    else:
        app.display_success(f'Trusted local config: `{local_config_path}`')

    app.display_info(
        'Trust is bound to this file hash; any edit revokes trust until you run `ddev config allow` again.'
    )
