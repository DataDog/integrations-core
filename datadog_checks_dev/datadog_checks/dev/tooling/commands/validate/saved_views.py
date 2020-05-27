# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from ...utils import complete_valid_checks, get_saved_views, load_saved_views, load_manifest, read_metadata_rows
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_success, echo_warning

REQUIRED_HEADERS = {'name', 'type', 'page', 'query'}

OPTIONAL_HEADERS = {'timerange', 'visible_facets', 'options'}

ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS

@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate saved view files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def saved_views(check):
    all_saved_views = get_saved_views(check)
    
    for saved_view in all_saved_views:
        view = load_saved_views(saved_view)
        print(view)
