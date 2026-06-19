# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Trust the local .ddev.toml so its _fetch_command fields are executed')
@click.pass_obj
def allow(app: Application):
    """Mark the local ``.ddev.toml`` as trusted.

    When trusted, ``*_fetch_command`` fields in the override file are executed to
    resolve secret values.  The current file hash is stored; if the file
    changes the trust is automatically revoked and a warning is shown.
    """
    from ddev.config.override_trust import upsert_trust_entry

    if not app.config_file.overrides_available():
        app.abort(f'No {".ddev.toml"} file found in the current directory or any parent directory.')

    upsert_trust_entry(
        overrides_path=app.config_file.overrides_path,
        global_config_dir=app.config_file.global_path.parent,
        state='allowed',
    )
    app.display_success(f'Trusted: {app.config_file.pretty_overrides_path}')
