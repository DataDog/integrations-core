# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.config.file import DDEV_TOML
from ddev.config.trust import TrustStorePersistenceError, deny_local_config
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Revoke trust for local secret command fields')
@click.pass_obj
def deny(app: Application):
    """Revoke trust for the current repo-local `.ddev.toml` file."""
    local_config_path = (
        app.config_file.overrides_path if app.config_file.overrides_available() else Path.cwd() / DDEV_TOML
    )
    try:
        removed = deny_local_config(local_config_path)
    except TrustStorePersistenceError as e:
        app.abort(str(e))

    if removed:
        app.display_success(f'Removed trust for local config: `{local_config_path}`')
    else:
        app.display_info(f'Local config is already untrusted: `{local_config_path}`')
