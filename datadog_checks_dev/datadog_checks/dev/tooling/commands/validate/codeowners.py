# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from ...utils import get_codeowners, get_codeowners_file, get_valid_integrations
from ..console import CONTEXT_SETTINGS, abort, annotate_error, echo_failure, echo_success

DIRECTORY_REGEX = re.compile(r"\/(.*)\/$")

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
def codeowners():
    """Validate that every integration has an entry in the `CODEOWNERS` file."""

    has_failed = False
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

    if not has_failed:
        echo_success("All integrations have valid codeowners.")
    else:
        abort()
