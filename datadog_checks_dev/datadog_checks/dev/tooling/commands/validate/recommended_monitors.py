# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import click

from ....utils import file_exists, read_file, write_file
from ...constants import get_root
from ...utils import get_valid_integrations, load_manifest, parse_version_parts
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

REQUIRED_ATTRIBUTES = {'name', 'type', 'query', 'message', 'tags', 'options', 'recommended_monitor_metadata'}

## Questions
## 1 monitor per file
## File must be mentioned in manifest.json


@click.command('recommended-monitors', context_settings=CONTEXT_SETTINGS, short_help='Validate recommended monitor files')
def recommended_monitors():
    """Validate all `service_checks.json` files."""
    root = get_root()
    echo_info("Validating all service_checks.json files...")
    failed_checks = 0
    ok_checks = 0
