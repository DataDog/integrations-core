# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from datadog_checks.dev.tooling.utils import get_valid_integrations, get_check_files, get_default_config_spec

from ..console import CONTEXT_SETTINGS, echo_info, echo_failure

# Integrations that are not fully updated to http wrapper class but is owned partially by a different organization
EXCLUDED_INTEGRATIONS = {
    'kubelet',
    'openstack'
}

REQUEST_LIBRARY_FUNCTIONS = {
    'requests.get',
    'requests.post',
    'requests.head',
    'requests.put',
    'requests.patch',
    'requests.delete'
}

SPEC_CONFIG_HTTP = {
    'instances/http',
    'init_config/http'
}


def validate_config_http(file, check):
    """Determines if integration with http wrapper class
    uses the http template in its spec.yaml file.

    file -- filepath of file to validate
    check -- name of the check that file belongs to
    """

    if os.path.exists(file):
        has_instance_http = False
        has_init_config_http = False
        with open(file, "r") as f:
            for _, line in enumerate(f):
                if 'instances/http' in line:
                    has_instance_http = True
                if 'init_config/http' in line:
                    has_init_config_http = True

        if not has_instance_http:
            echo_failure(f'Detected {check}\'s spec.yaml file does not contain `instances/http` '
                         f'but {check} uses http wrapper')

        if not has_init_config_http:
            echo_failure(f'Detected {check}\'s spec.yaml file does not contain `init_config/http` '
                         f'but {check} uses http wrapper')


def validate_use_http_wrapper(file, check):
    """Return true if the file uses the http wrapper class.
    Otherwise outputs every instance of request library function use

    file -- filepath of file to validate
    check -- name of the check that file belongs to
    """

    with open(file, "r") as f:
        for num, line in enumerate(f):
            if 'self.http' in line:
                return True

            for http_func in REQUEST_LIBRARY_FUNCTIONS:
                if http_func in line:
                    echo_failure(f'Check \'{check}\' uses \'{http_func}\' on line {num} in \'{os.path.basename(file)}\''
                                 f', please use the HTTP wrapper instead')

    return False


@click.command('http', context_settings=CONTEXT_SETTINGS, short_help='Validate usage of http wrapper')
def http():
    """Validate all integrations for usage of http wrapper."""
    echo_info("Validating all integrations for usage of http wrapper...")

    for check in sorted(get_valid_integrations()):
        uses_http_wrapper = False
        # Validate use of http wrapper (self.http.[...]) in check's .py files
        if check not in EXCLUDED_INTEGRATIONS:
            for file in get_check_files(check, include_tests=False):
                uses_http_wrapper = validate_use_http_wrapper(file, check)

        # Validate use of http template in check's spec.yaml (if exists)
        if uses_http_wrapper:
            validate_config_http(get_default_config_spec(check), check)

    echo_info('Completed http validation!')
