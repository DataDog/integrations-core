# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import click

from ddev.utils.codeowners import CodeOwners

if TYPE_CHECKING:
    from ddev.cli.application import Application

DIRECTORY_REGEX = re.compile(r"\/(.*)\/$")

LOGS_TEAM = '@DataDog/logs-integrations-reviewers'

# Integrations that are known to be tiles and have email-based codeowners
IGNORE_TILES = {
    '1e',
    'auth0',
    'bluematador',
    'bonsai',
    'buddy',
    'concourse_ci',
    'f5-distributed-cloud',
    'launchdarkly',
    'lacework',
    'gremlin',
    'perimeterx',
    'rigor',
    'rookout',
    'rundeck',
    'sqreen',
    'squadcast',
}


def _get_valid_integrations(app: Application) -> list[str]:
    """Return the names of integrations (directories containing manifest.json)."""
    return sorted(integration.name for integration in app.repo.integrations.iter(['all']))


def _create_codeowners_resolver(codeowners_lines: list[str]) -> CodeOwners:
    return CodeOwners("\n".join(codeowners_lines))


def _validate_logs_assets_codeowners(app: Application, codeowners_lines: list[str]) -> list[str]:
    """Validate that `CODEOWNERS` assigns the logs team as owner for all log assets."""
    failed_integrations: list[str] = []
    owners_resolver = _create_codeowners_resolver(codeowners_lines)
    for integration in _get_valid_integrations(app):
        logs_assets_owners = owners_resolver.of(f"/{integration}/assets/logs/")
        path = app.repo.path / integration / 'assets' / 'logs'
        if ("TEAM", LOGS_TEAM) not in logs_assets_owners and path.exists():
            failed_integrations.append(integration)

    return failed_integrations


def _create_codeowners_map(app: Application, codeowners_lines: list[str]) -> dict[str, str | None]:
    """Map each integration to its codeowner entry (or None / "empty")."""
    all_integrations = _get_valid_integrations(app)
    codeowner_map: dict[str, str | None] = dict.fromkeys(all_integrations)

    # each valid entry looks something like:
    # /containerd/                              @DataDog/container-integrations @DataDog/agent-integrations
    for entry in codeowners_lines:
        parts = [part for part in entry.split(" ") if part != "" and part != "\t"]
        match = DIRECTORY_REGEX.match(parts[0])
        if match and match.group(1):
            if len(parts) < 2:
                codeowner_map[match.group(1)] = "empty"
            else:
                codeowner_map[match.group(1)] = parts[1]

    return codeowner_map


@click.command(short_help='Validate `CODEOWNERS` file has an entry for each integration')
@click.pass_obj
def codeowners(app: Application):
    """Validate that every integration has an entry in the `CODEOWNERS` file."""
    codeowners_file = app.repo.path / '.github' / 'CODEOWNERS'
    codeowners_lines = codeowners_file.read_text().splitlines(keepends=True)

    has_failed = False
    is_core_check = app.repo.name == 'core'

    if not is_core_check:  # We do not need this rule in integrations-core
        codeowner_map = _create_codeowners_map(app, codeowners_lines)
        for integration, codeowner in codeowner_map.items():
            if not codeowner:
                has_failed = True
                message = f"Integration {integration} does not have a valid `CODEOWNERS` entry."
                app.display_error(message)
            elif codeowner == "empty":
                has_failed = True
                message = f"Integration {integration} has a `CODEOWNERS` entry, but the codeowner is empty."
                app.display_error(message)
            elif not codeowner.startswith("@") and integration not in IGNORE_TILES:
                has_failed = True
                message = (
                    f"Integration {integration} has a `CODEOWNERS` entry, but the codeowner is not a username or team."
                )
                app.display_error(message)

    failed_integrations = _validate_logs_assets_codeowners(app, codeowners_lines)
    if has_failed or failed_integrations:
        for integration in failed_integrations:
            app.display_error(f"/{integration}/assets/logs/ is not owned by {LOGS_TEAM}")
        app.abort()
    else:
        app.display_success("All integrations have valid codeowners.")
