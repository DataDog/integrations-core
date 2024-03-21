# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

import click

from ...codeowners import CodeOwners
from ...constants import get_root
from ...utils import get_codeowners, get_codeowners_file, get_valid_integrations
from ..console import CONTEXT_SETTINGS, abort, annotate_error, echo_failure, echo_success

DIRECTORY_REGEX = re.compile(r"\/(.*)\/$")

LOGS_TEAM = '@DataDog/logs-backend'

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


def create_codeowners_resolver():
    """Creates an object that resolves owners for files in a repo."""
    owners_resolver = CodeOwners("\n".join(get_codeowners()))
    return owners_resolver


def validate_logs_assets_codeowners():
    """Validate `CODEOWNERS` assigns logs as owner for all log assets."""

    failed_integrations = []
    owners_resolver = create_codeowners_resolver()
    all_integrations = sorted(get_valid_integrations())
    for integration in all_integrations:
        logs_assets_owners = owners_resolver.of(f"/{integration}/assets/logs/")
        path = os.path.join(get_root(), integration, 'assets', 'logs')
        if ("TEAM", LOGS_TEAM) not in logs_assets_owners and os.path.exists(path):
            failed_integrations.append(integration)

    return failed_integrations


def create_codeowners_map():
    """Creates a mapping of integrations to codeowners entries"""
    codeowners = get_codeowners()
    all_integrations = sorted(get_valid_integrations())
    codeowner_map = dict.fromkeys(all_integrations)

    # each valid entry looks something like:
    # /containerd/                              @DataDog/container-integrations @DataDog/agent-integrations
    for entry in codeowners:
        parts = [part for part in entry.split(" ") if part != "" and part != "\t"]
        match = DIRECTORY_REGEX.match(parts[0])
        if match and match.group(1):
            if len(parts) < 2:
                codeowner_map[match.group(1)] = "empty"
            else:
                codeowner_map[match.group(1)] = parts[1]

    return codeowner_map


@click.command(
    context_settings=CONTEXT_SETTINGS, short_help='Validate `CODEOWNERS` file has an entry for each integration'
)
@click.pass_context
def codeowners(ctx):
    """Validate that every integration has an entry in the `CODEOWNERS` file."""

    has_failed = False
    is_core_check = ctx.obj['repo_choice'] == 'core'

    if not is_core_check:  # We do not need this rule in integrations-core
        codeowner_map = create_codeowners_map()
        codeowners_file = get_codeowners_file()
        for integration, codeowner in codeowner_map.items():
            if not codeowner:
                has_failed = True
                message = f"Integration {integration} does not have a valid `CODEOWNERS` entry."
                echo_failure(message)
                annotate_error(codeowners_file, message)
            elif codeowner == "empty":
                has_failed = True
                message = f"Integration {integration} has a `CODEOWNERS` entry, but the codeowner is empty."
                echo_failure(message)
                annotate_error(codeowners_file, message)
            elif not codeowner.startswith("@") and integration not in IGNORE_TILES:
                has_failed = True
                message = (
                    f"Integration {integration} has a `CODEOWNERS` entry, but the codeowner is not a username or team."
                )
                echo_failure(message)
                annotate_error(codeowners_file, message)

    failed_integrations = validate_logs_assets_codeowners()
    if has_failed or failed_integrations:
        for integration in failed_integrations:
            echo_failure(f"/{integration}/assets/logs/ is not owned by {LOGS_TEAM}")
        abort()
    else:
        echo_success("All integrations have valid codeowners.")
