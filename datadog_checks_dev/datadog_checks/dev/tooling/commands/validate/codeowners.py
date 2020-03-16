# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import click

from ....utils import file_exists, read_file, write_file
from ...constants import get_root
from ...utils import get_valid_integrations, load_manifest, get_codeowners, get_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success



@click.command('codeowners', context_settings=CONTEXT_SETTINGS, short_help='Validate `CODEOWNERS` file has an entry for each integration')
def codeowners():
    """Validate all `CODEOWNERS` file."""

    all_checks = get_valid_checks()

    codeowners = get_codeowners()

    for i in codeowners:
        print("hi" + i)
    #for check in all_checks:


