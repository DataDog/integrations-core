# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations
from typing import TYPE_CHECKING

import click

from datadog_checks.dev.subprocess import run_command

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help="Remove a project's build artifacts")
@click.pass_obj
def clean(app: Application):
    """
    Remove build and test artifacts for the given CHECK. If CHECK is not
    specified, the current working directory is used.
    """
    with app.repo.path.as_cwd():
        app.platform.run_command(["git", "clean", "-fdX", "-e", "!.vscode", "-e", "!.idea"])
