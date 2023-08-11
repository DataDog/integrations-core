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

REQUEST_LIBRARY_FUNC_RE = r'requests.[get|post|head|put|patch|delete]*\('
HTTP_WRAPPER_INIT_CONFIG_RE = r'init_config\/[http|openmetrics_legacy|openmetrics]*'
HTTP_WRAPPER_INSTANCE_RE = r'instances\/[http|openmetrics_legacy|openmetrics]*'


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
            f'Detected {check} is missing `instances/http` or `instances/openmetrics_legacy` template in spec.yaml'
        )
        error_message.append(message)

        has_failed = True

    if not has_init_config_http:
        message = (
            f'Detected {check} is missing `init_config/http` or `init_config/openmetrics_legacy` template in spec.yaml'
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
        found_match_arg = re.search(r'auth=|header=', read_file)
        found_http = re.search(r'self.http|OpenMetricsBaseCheck', read_file)
        skip_validation = re.search(r'SKIP_HTTP_VALIDATION', read_file)
        http_func = re.search(REQUEST_LIBRARY_FUNC_RE, read_file)
        if http_func and not skip_validation:
            error_message += (
                f'Check `{check}` uses `{http_func.group(0)}` in `{os.path.basename(file)}`, '
                f'please use the HTTP wrapper instead\n'
                f'If this a genuine usage of the parameters, '
                f'please inline comment `# SKIP_HTTP_VALIDATION`'
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
                    f'The HTTP wrapper contains parameter `{has_arg_warning.group().replace("=", "")}`, '
                    f'this configuration is handled by the wrapper automatically.\n'
                    f'If this a genuine usage of the parameters, '
                    f'please inline comment `# SKIP_HTTP_VALIDATION`'
                )
                pass

    if has_failed:
        return check_uses_http_wrapper, warning_message, error_message
    return check_uses_http_wrapper, warning_message, error_message


@click.command(short_help='Validate HTTP usage')
@click.argument('integrations', nargs=-1)
@click.pass_obj
def http(app: Application, integrations: tuple[str, ...]):
    """Validate all integrations for usage of HTTP wrapper.

    If `integrations` is specified, only those will be validated,
    an 'all' `check` value will validate all checks.
    """
    validation_tracker = app.create_validation_tracker('HTTP wrapper validation')

    excluded = set(app.repo.config.get('/overrides/validate/http/exclude', []))
    for integration in app.repo.integrations.iter(integrations):
        if integration.name in excluded or not integration.is_integration:
            continue

        check_uses_http_wrapper, warning_message, error_message = validate_use_http_wrapper(integration.name, app)

        if warning_message:
            validation_tracker.warning((integration.display_name,), message=warning_message)
        if error_message:
            validation_tracker.error((integration.display_name,), message=error_message)
        # Validate use of http template in check's spec.yaml (if exists)
        if check_uses_http_wrapper:
            validate_config_result = validate_config_http(str(integration.config_spec), integration.name)
            if validate_config_result:
                _, config_http_msg = validate_config_result
                validation_tracker.error((integration.display_name,), message='\n'.join(config_http_msg))
            else:
                validation_tracker.success()
        else:
            if not error_message:
                validation_tracker.success()

    validation_tracker.display()
    if validation_tracker.errors:
        app.abort()
