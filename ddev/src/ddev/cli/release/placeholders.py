# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
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
    from ddev.release.placeholders import (
        RETIRED_PLACEHOLDER_NAMES,
        PlaceholderOrchestrator,
        get_api_token,
        needs_placeholder,
        placeholder_package_names,
        resolve_placeholder_name,
    )

    package_names = placeholder_package_names(app.repo)
    if names:
        resolved_names = []
        for requested in names:
            resolved = resolve_placeholder_name(requested, package_names)
            if resolved is None:
                app.abort(f'Unknown integration or package name: {requested}')
            resolved_names.append(resolved)
        resolved_names = sorted(set(resolved_names))
        selected = [name for name in resolved_names if needs_placeholder(name)]
        for name in set(resolved_names) - set(selected):
            app.display_info(f'  skip {name} (already published)')
    else:
        candidates = sorted(set(package_names.values()) | set(RETIRED_PLACEHOLDER_NAMES))
        selected = [name for name in candidates if needs_placeholder(name)]

    if not selected:
        app.display_success('Nothing to publish.')
        return

    if dry_run:
        for name in selected:
            app.display_info(name)
        return

    token = get_api_token()
    oidc_publishing = 'ACTIONS_ID_TOKEN_REQUEST_URL' in os.environ and 'ACTIONS_ID_TOKEN_REQUEST_TOKEN' in os.environ
    if token is None and not oidc_publishing:
        app.abort(
            'No PyPI API token available: set DDEV_PYPI_TOKEN, enter one at the prompt, '
            'or run in GitHub Actions with trusted publishing.'
        )

    orchestrator = PlaceholderOrchestrator(app, selected, token)
    orchestrator.run()

    if orchestrator.had_failures:
        app.abort()
