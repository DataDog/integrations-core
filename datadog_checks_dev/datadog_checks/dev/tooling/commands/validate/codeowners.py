# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from ...utils import get_codeowners, get_valid_integrations
from ..console import CONTEXT_SETTINGS, echo_failure, echo_success

DIRECTORY_REGEX = re.compile(r"\/(.*)\/$")


def get_all_integrations_with_codeowners():
    """ Returns a list of all integrations that have a codeowner"""
    codeowners = get_codeowners()

    integrations_with_codeowners = set()
    integrations_with_only_entries = set()

    # each valid entry looks something like:
    # /containerd/                              @DataDog/container-integrations @DataDog/agent-integrations
    for entry in codeowners:
        parts = [part for part in entry.split(" ") if part != "" and part != "\t"]
        if not parts:
            continue
        match = DIRECTORY_REGEX.match(parts[0])
        if match and match.group(1):
            integration = match.group(1)
            if len(parts) != 2:
                integrations_with_only_entries.add(integration)
            else:
                integrations_with_codeowners.add(integration)
    return integrations_with_codeowners, integrations_with_only_entries


@click.command(
    'codeowners',
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate `CODEOWNERS` file has an entry for each integration',
)
def codeowners():
    """Validate that every integration has an entry in the `CODEOWNERS` file."""
    all_integrations_with_codeowners, integrations_with_only_entries = get_all_integrations_with_codeowners()
    all_integrations = get_valid_integrations()
    has_failed = False

    for integration in all_integrations:
        if integration in integrations_with_only_entries:
            has_failed = True
            echo_failure(f"Integration {integration} has a `CODEOWNERS` entry, but the codeowner is empty.")
        elif integration not in all_integrations_with_codeowners:
            has_failed = True
            echo_failure(f"Integration {integration} does not have a valid `CODEOWNERS` entry.")

    if not has_failed:
        echo_success("All integrations have codeowners.")
