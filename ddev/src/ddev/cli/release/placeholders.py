# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Claim PyPI placeholder package names')
@click.argument('names', nargs=-1)
@click.option('--dry-run', is_flag=True, help='List the packages that would be published, then exit.')
@click.pass_obj
def placeholders(app: Application, names: tuple[str, ...], dry_run: bool) -> None:
    """Publish placeholder packages to PyPI.

    With NAMES, publish only those integrations; each name may be an integration name (n8n) or a
    package name (datadog-n8n), and packages whose PyPI release is newer than the empty 0.0.1
    placeholder are skipped. Without NAMES, publish every package whose PyPI release is missing
    or still the empty 0.0.1 placeholder.

    Authentication: in GitHub Actions with `id-token: write`, each package mints a short-lived
    token through trusted publishing. Anywhere else, set DDEV_PYPI_TOKEN or enter a token at the
    prompt; the token is never accepted as a command-line flag so it cannot leak through history.
    """
    from ddev.release.placeholders import PlaceholderPorts, publish_placeholders

    if app.repo.name != 'core':
        app.abort('This command can only be run against the core repository.')

    def notify(level: str, text: str) -> None:
        if level == 'error':
            app.display_error(text, markup=False)
        elif level == 'success':
            app.display_success(text, markup=False)
        else:
            app.display_info(text, markup=False)

    ports = PlaceholderPorts(notify=notify, prompt=app.prompt, interactive=lambda: app.interactive)

    try:
        report = publish_placeholders(app.repo, names, dry_run, ports=ports)
    except ValueError as error:
        app.abort(str(error))

    if dry_run:
        for name in report.selected:
            app.display(name)
    if report.failed:
        app.abort()
    if not report.selected:
        app.display_success('Nothing to publish.')
