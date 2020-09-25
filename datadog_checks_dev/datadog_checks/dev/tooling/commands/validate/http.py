# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.utils import get_valid_integrations, get_check_files

from ..console import echo_success, abort, CONTEXT_SETTINGS, echo_info, echo_debug, echo_warning, echo_failure

REQUEST_LIBRARY_FUNCTIONS = {
    'request.get',
    'request.post',
    'request.head',
    'request.put',
    'request.patch',
    'request.delete'
}


def validate_use_http_wrapper(file, check):
    for http_func in REQUEST_LIBRARY_FUNCTIONS:
        with open(file, "r") as f:
            if http_func in f.read():
                echo_warning(f'Detected {http_func} in {check}\' {file}, '
                             f'please make sure to use http wrapper class instead of request library')


@click.command('http', context_settings=CONTEXT_SETTINGS, short_help='Validate usage of http wrapper')
def http():
    """Validate all integrations for usage of http wrapper."""
    echo_info("Validating all integrations for usage of http wrapper...")

    validate_use_http_wrapper('/Users/andrew.zhang/integrations-core/aerospike/datadog_checks/aerospike/aerospike.py',
                              'aerospike')

    # for check_name in sorted(get_valid_integrations()):
        # for file in get_check_files(check_name, include_tests=False):
        #     validate_use_http_wrapper(file, check_name)
        # also validate if config has http

    echo_success(f"ur smart")
