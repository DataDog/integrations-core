# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import os
import click
import mmap

from ...utils import get_valid_integrations, get_test_directory
from ..console import CONTEXT_SETTINGS, echo_failure, echo_success

BAD_CHECK_REGEX = re.compile(r"(\s[[:alpha:]]*\(\S*,\s?\S*,\s?\S*,\s?\S*\))")


def has_legacy_check(check):
    for path, _, files in os.walk(get_test_directory(check)):
        for fn in files:
            if fn.endswith('.py'):
                with open(os.path.join(path, fn)) as test_file:
                    for line in test_file:
                        matches = BAD_CHECK_REGEX.match(str(line))
                        if matches:
                            for match in matches:
                                print(match)


@click.command(
    'legacy-signature',
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate that no integration uses the legacy signature',
)
def legacy_signature():
    """Validate that no integration uses the legacy signature."""
    integrations = get_valid_integrations()
    for integration in integrations:
        print(integration)
        has_legacy_check(integration)
    return
