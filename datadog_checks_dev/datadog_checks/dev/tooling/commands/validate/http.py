# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from datadog_checks.dev.tooling.utils import get_valid_integrations, get_check_files, get_config_spec

from ..console import CONTEXT_SETTINGS, echo_info, echo_warning

REQUEST_LIBRARY_FUNCTIONS = {
    'requests.get',
    'requests.post',
    'requests.head',
    'requests.put',
    'requests.patch',
    'requests.delete'
}


def validate_config_http(file, check):
    config_valid = True
    if os.path.isfile(file):
        with open(file, "r") as f:
            if 'instances/http' not in f.read():
                echo_warning(f'{check}\'s spec.yaml file does not contain `instances/http` '
                             f'but {check} uses http wrapper')

    return config_valid


def validate_use_http_wrapper(file, check):
    uses_http_wrapper = False

    with open(file, "r") as f:
        for num, line in enumerate(f):
            if 'self.http' in line:
                uses_http_wrapper = True

            for http_func in REQUEST_LIBRARY_FUNCTIONS:
                if http_func in line:
                    echo_warning(f'Detected `{http_func}` on line {num} in {check}\'s {file}, '
                                 f'please make sure to use http wrapper class instead of request library')
    return uses_http_wrapper


@click.command('http', context_settings=CONTEXT_SETTINGS, short_help='Validate usage of http wrapper')
def http():
    """Validate all integrations for usage of http wrapper."""
    echo_info("Validating all integrations for usage of http wrapper...")

    for check in sorted(get_valid_integrations()):
        uses_http_wrapper = False
        # validate use of http wrapper (self.http.[...]) in check's .py files
        for file in get_check_files(check, include_tests=False):
            uses_http_wrapper = validate_use_http_wrapper(file, check)

        # validate use of `instances/http` in check's config files
        if uses_http_wrapper:
            validate_config_http(get_config_spec(check), check)

    echo_info('Completed http validation!')
