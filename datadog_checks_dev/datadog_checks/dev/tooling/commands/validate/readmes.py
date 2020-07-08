# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import click

from ...utils import complete_valid_checks, get_saved_views, get_valid_integrations, load_saved_views
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_success

@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate README.md files')
@click.argument('integration', autocompletion=complete_valid_checks, required=False)
def readmes(integration):
    """Validates README files

    If `check` is specified, only the check will be validated,
    otherwise all README files in the repo will be.
    """
    errors = False
