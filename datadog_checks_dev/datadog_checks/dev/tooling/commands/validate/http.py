# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from datadog_checks.dev.tooling.utils import get_check_files, get_default_config_spec, get_valid_integrations

from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

# Integrations that are not fully updated to http wrapper class but is owned partially by a different organization
EXCLUDED_INTEGRATIONS = {'kubelet', 'openstack'}

REQUEST_LIBRARY_FUNCTIONS = {
    'requests.get',
    'requests.post',
    'requests.head',
    'requests.put',
    'requests.patch',
    'requests.delete',
    'requests.options',
}


def validate_config_http(file, check):
    """Determines if integration with http wrapper class
    uses the http template in its spec.yaml file.

    file -- filepath of file to validate
    check -- name of the check that file belongs to
    """

    if not os.path.exists(file):
        return

    has_instance_http = False
    has_init_config_http = False
    has_failed = False
    with open(file, 'r', encoding='utf-8') as f:
        for _, line in enumerate(f):
            if 'instances/http' in line or 'instances/openmetrics_legacy' in line:
                has_instance_http = True
            if 'init_config/http' in line or 'init_config/openmetrics_legacy' in line:
                has_init_config_http = True

    if not has_instance_http:
        echo_failure(
            f"Detected {check} is missing `instances/http` or `instances/openmetrics_legacy` template in spec.yaml"
        )
        has_failed = True

    if not has_init_config_http:
        echo_failure(
            f"Detected {check} is missing `init_config/http` or `init_config/openmetrics_legacy` template in spec.yaml"
        )
        has_failed = True

    return has_failed


def validate_use_http_wrapper_file(file, check):
    """Return true if the file uses the http wrapper class.
    Also outputs every instance of deprecated request library function use

    file -- filepath of file to validate
    check -- name of the check
    """
    file_uses_http_wrapper = False
    has_failed = False
    with open(file, 'r', encoding='utf-8') as f:
        for num, line in enumerate(f):
            if ('self.http' in line or 'OpenMetricsBaseCheck' in line) and 'SKIP_HTTP_VALIDATION' not in line:
                return True, has_failed

            for http_func in REQUEST_LIBRARY_FUNCTIONS:
                if http_func in line:
                    echo_failure(
                        f'Check `{check}` uses `{http_func}` on line {num} in `{os.path.basename(file)}`, '
                        f'please use the HTTP wrapper instead'
                    )
                    has_failed = True

    return file_uses_http_wrapper, has_failed


def validate_use_http_wrapper(check):
    """Return true if the check uses the http wrapper class in any of its files.
    If any of the check's files uses the request library, abort.

    check -- name of the check
    """
    has_failed = False
    check_uses_http_wrapper = False
    for file in get_check_files(check, include_tests=False):
        if file.endswith('.py'):
            file_uses_http_wrapper, file_uses_request_lib = validate_use_http_wrapper_file(file, check)
            has_failed = has_failed or file_uses_request_lib
            check_uses_http_wrapper = check_uses_http_wrapper or file_uses_http_wrapper

    if has_failed:
        abort()
    return check_uses_http_wrapper


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate usage of http wrapper')
def http():
    """Validate all integrations for usage of http wrapper."""

    has_failed = False
    echo_info("Validating all integrations for usage of http wrapper...")
    for check in sorted(get_valid_integrations()):
        check_uses_http_wrapper = False

        # Validate use of http wrapper (self.http.[...]) in check's .py files
        if check not in EXCLUDED_INTEGRATIONS:
            check_uses_http_wrapper = validate_use_http_wrapper(check)

        # Validate use of http template in check's spec.yaml (if exists)
        if check_uses_http_wrapper:
            has_failed = validate_config_http(get_default_config_spec(check), check) or has_failed

    if has_failed:
        abort()

    echo_success('Completed http validation!')
