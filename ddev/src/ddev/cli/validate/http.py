# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
EXCLUDED_INTEGRATIONS = {'kubelet', 'openstack'}

REQUEST_LIBRARY_FUNC_RE = r"requests.[get|post|head|put|patch|delete]*\("
HTTP_WRAPPER_INIT_CONFIG_RE = r"init_config\/[http|openmetrics_legacy|openmetrics]*"
HTTP_WRAPPER_INSTANCE_RE = r"instances\/[http|openmetrics_legacy|openmetrics]*"


def get_default_config_spec(check_name, app):
    return os.path.join(app.repo.path, check_name, 'assets', 'configuration', 'spec.yaml')


def validate_config_http(file, check):
    """Determines if integration with http wrapper class
    uses the http template in its spec.yaml file.

    file -- filepath of file to validate
    check -- name of the check that file belongs to
    """
    error_message = []
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
        error_message.append(message)

        has_failed = True

    if not has_init_config_http:
        message = (
            f"Detected {check} is missing `init_config/http` or `init_config/openmetrics_legacy` template in spec.yaml"
        )

        error_message.append(message)
        has_failed = True

    return has_failed, error_message


def validate_use_http_wrapper_file(file, check):
    """Return true if the file uses the http wrapper class.
    Also outputs every instance of deprecated request library function use

    file -- filepath of file to validate
    check -- name of the check
    """
    file_uses_http_wrapper = False
    has_failed = False
    error_message = ''
    with open(file, 'r', encoding='utf-8') as f:
        read_file = f.read()
        found_match_arg = re.search(r"auth=|header=", read_file)
        found_http = re.search(r"self.http|OpenMetricsBaseCheck", read_file)
        skip_validation = re.search(r"SKIP_HTTP_VALIDATION", read_file)
        http_func = re.search(REQUEST_LIBRARY_FUNC_RE, read_file)
        if http_func and not skip_validation:
            error_message += (
                f'Check `{check}` uses `{http_func.group(0)}` in `{os.path.basename(file)}`, '
                f'please use the HTTP wrapper instead\n'
                f"If this a genuine usage of the parameters, "
                f"please inline comment `# SKIP_HTTP_VALIDATION`\n"
            )
            return False, True, None, error_message
        if found_http and not skip_validation:
            return found_http, has_failed, found_match_arg, error_message

    return file_uses_http_wrapper, has_failed, None, error_message


def validate_use_http_wrapper(check, app):
    """Return true if the check uses the http wrapper class in any of its files.
    If any of the check's files uses the request library, abort.

    check -- name of the check
    """
    has_failed = False
    check_uses_http_wrapper = False
    warning_message = ''
    error_message = ''
    for file in app.repo.integrations.get(check).package_files():
        file_str = str(file)
        if file_str.endswith('.py'):
            file_uses_http_wrapper, file_uses_request_lib, has_arg_warning, error = validate_use_http_wrapper_file(
                file_str, check
            )
            has_failed = has_failed or file_uses_request_lib
            error_message += error
            check_uses_http_wrapper = check_uses_http_wrapper or file_uses_http_wrapper
            if check_uses_http_wrapper and has_arg_warning:
                # Check for headers= or auth=
                warning_message += (
                    f"    The HTTP wrapper contains parameter `{has_arg_warning.group().replace('=', '')}`, "
                    f"this configuration is handled by the wrapper automatically.\n"
                    f"    If this a genuine usage of the parameters, "
                    f"please inline comment `# SKIP_HTTP_VALIDATION`\n"
                )
                pass

    if has_failed:
        return check_uses_http_wrapper, warning_message, error_message
    return check_uses_http_wrapper, warning_message, error_message


@click.command(short_help='Validate usage of http wrapper')
@click.argument('check', nargs=-1)
@click.pass_obj
def http(app: Application, check: tuple[str, ...]):
    """Validate all integrations for usage of http wrapper.

    If `check` is specified, only the check will be validated,
    an 'all' `check` value will validate all checks.
    """
    validation_tracker = app.create_validation_tracker('HTTP wrapper validation')
    has_failed = False

    check_iterable = app.repo.integrations.iter(check)
    app.display_info(f"Validating {sum(1 for _ in check_iterable)} integrations for usage of http wrapper...")

    for curr_check in app.repo.integrations.iter(check):
        check_uses_http_wrapper = False

        # Validate use of http wrapper (self.http.[...]) in check's .py files
        if curr_check.name not in EXCLUDED_INTEGRATIONS:
            check_uses_http_wrapper, warning_message, error_message = validate_use_http_wrapper(curr_check.name, app)

        if warning_message:
            validation_tracker.warning((curr_check.display_name,), message=warning_message)
        if error_message:
            has_failed = True
            validation_tracker.error((curr_check.display_name,), message=error_message)
        # Validate use of http template in check's spec.yaml (if exists)
        if check_uses_http_wrapper:
            validate_config_result = validate_config_http(
                get_default_config_spec(curr_check.name, app), curr_check.name
            )
            if validate_config_result:
                config_http_failure, config_http_msg = validate_config_result
                has_failed = config_http_failure or has_failed
                validation_tracker.error((curr_check.display_name,), message='\n'.join(config_http_msg))
            else:
                validation_tracker.success()
        else:
            if not error_message:
                validation_tracker.success()

    if has_failed:
        validation_tracker.display()
        app.abort()
    else:
        validation_tracker.display()
