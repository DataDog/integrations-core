# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help="Remove all build artifacts")
@click.pass_obj
def clean(app: Application):
    """
    Remove build and test artifacts for the entire repository.
    """
    with app.repo.path.as_cwd(), app.status("Cleaning repository"):
        app.platform.run_command(
            ["git", "clean", "-fdX", "-e", "!.vscode", "-e", "!.idea", "-e", "!ddev/src/ddev/_version.py"]
        )
