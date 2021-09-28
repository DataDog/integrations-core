# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

import click

from datadog_checks.dev.tooling.annotations import annotate_error
from datadog_checks.dev.tooling.utils import complete_valid_checks, get_check_files, get_default_config_spec

from ...testing import process_checks_option
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

# Integrations that are not fully updated to http wrapper class but is owned partially by a different organization

EXCLUDED_INTEGRATIONS = {'kubelet', 'openstack'}

REQUEST_LIBRARY_FUNC_RE = r"requests.[get|post|head|put|patch|delete]*\("
HTTP_WRAPPER_INIT_CONFIG_RE = r"init_config\/[http|openmetrics_legacy|openmetrics]*"
HTTP_WRAPPER_INSTANCE_RE = r"instances\/[http|openmetrics_legacy|openmetrics]*"


def validate_config_http(file, check):
    """Determines if integration with http wrapper class
    uses the http template in its spec.yaml file.

    file -- filepath of file to validate
    check -- name of the check that file belongs to
    """

    if not os.path.exists(file):
        return

    has_failed = False
    with open(file, 'r', encoding='utf-8') as f:
        read_file = f.read()
        has_init_config_http = re.search(HTTP_WRAPPER_INIT_CONFIG_RE, read_file)
        has_instance_http = re.search(HTTP_WRAPPER_INSTANCE_RE, read_file)
        if has_init_config_http and has_instance_http:
            return

    if not has_instance_http:
        message = (
            f"Detected {check} is missing `instances/http` or `instances/openmetrics_legacy` template in spec.yaml"
        )
        echo_failure(message)
        annotate_error(file, message)
        has_failed = True

    if not has_init_config_http:
        message = (
            f"Detected {check} is missing `init_config/http` or `init_config/openmetrics_legacy` template in spec.yaml"
        )
        echo_failure(message)
        annotate_error(file, message)
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
        read_file = f.read()
        found_match_arg = re.search(r"auth=|header=", read_file)
        found_http = re.search(r"self.http|OpenMetricsBaseCheck", read_file)
        skip_validation = re.search(r"SKIP_HTTP_VALIDATION", read_file)
        if found_http and not skip_validation:
            return found_http, has_failed, found_match_arg

        http_func = re.search(REQUEST_LIBRARY_FUNC_RE, read_file)
        if http_func:
            echo_failure(
                f'Check `{check}` uses `{http_func}` in `{os.path.basename(file)}`, '
                f'please use the HTTP wrapper instead'
            )
            annotate_error(
                file,
                "Detected use of `{}`, please use the HTTP wrapper instead".format(http_func),
            )
            return False, True, None

    return file_uses_http_wrapper, has_failed, None


def validate_use_http_wrapper(check):
    """Return true if the check uses the http wrapper class in any of its files.
    If any of the check's files uses the request library, abort.

    check -- name of the check
    """
    has_failed = False
    check_uses_http_wrapper = False
    for file in get_check_files(check, include_tests=False):
        if file.endswith('.py'):
            file_uses_http_wrapper, file_uses_request_lib, has_arg_warning = validate_use_http_wrapper_file(file, check)
            has_failed = has_failed or file_uses_request_lib
            check_uses_http_wrapper = check_uses_http_wrapper or file_uses_http_wrapper
            if check_uses_http_wrapper and has_arg_warning:
                # Check for headers= or auth=
                echo_warning(
                    f"{check}: \n"
                    f"    The HTTP wrapper contains parameter `{has_arg_warning.group().replace('=', '')}`, "
                    f"this configuration is handled by the wrapper automatically.\n"
                    f"    If this a genuine usage of the parameters, "
                    f"please inline comment `# SKIP_HTTP_VALIDATION`"
                )
                pass

    if has_failed:
        abort()
    return check_uses_http_wrapper


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate usage of http wrapper')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def http(check):
    """Validate all integrations for usage of http wrapper."""

    has_failed = False

    checks = process_checks_option(check, source='integrations')
    echo_info(f"Validating {len(checks)} integrations for usage of http wrapper...")

    for check in checks:
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
