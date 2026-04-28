# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.utils.fs import Path


def towncrier(
    app: Application, target_dir: Path | str, cmd: str, *cmd_args: str, display_output: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a towncrier subcommand against ``target_dir`` and return its completed process.

    By default the captured stdout is rendered via ``app.display`` as soon as towncrier
    finishes. Pass ``display_output=False`` to suppress that and let the caller format,
    redirect, or persist the output through the returned ``CompletedProcess``.

    A non-zero exit aborts the application with the combined stdout/stderr from towncrier.
    """
    config = app.repo.path / 'towncrier.toml'
    result = app.platform.run_command(
        [
            sys.executable,
            '-m',
            'towncrier',
            cmd,
            '--config',
            str(config),
            '--dir',
            str(target_dir),
            *cmd_args,
        ],
        capture_output=True,
        text=True,
    )
    stdout = result.stdout.rstrip()
    if stdout and (display_output or result.returncode):
        app.display(stdout, markup=False)
    if result.returncode:
        message = f'towncrier {cmd} exited with code {result.returncode}'
        stderr = result.stderr.rstrip()
        app.abort(f'{message}\n{stderr}' if stderr else message, code=result.returncode)
    return result
