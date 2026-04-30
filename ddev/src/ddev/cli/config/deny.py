# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Silence warnings about untrusted _fetch_command fields in .ddev.toml')
@click.pass_obj
def deny(app: Application):
    """Mark the local ``.ddev.toml`` as explicitly untrusted.

    ``*_fetch_command`` fields in the override file will be stripped silently
    (no warning shown).  Use ``ddev config allow`` to re-enable execution.
    """
    from ddev.config.override_trust import upsert_trust_entry

    if not app.config_file.overrides_available():
        app.abort(f'No {".ddev.toml"} file found in the current directory or any parent directory.')

    upsert_trust_entry(
        overrides_path=app.config_file.overrides_path,
        global_config_dir=app.config_file.global_path.parent,
        state='denied',
    )
    app.display_success(f'Silenced: {app.config_file.pretty_overrides_path}')
