# (C) Datadog, Inc. 2018-2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import yaml

from datadog_checks.dev.tooling.config_validator.validator import validate_config
from datadog_checks.dev.tooling.config_validator.validator_errors import SEVERITY_ERROR, SEVERITY_WARNING

from ....utils import basepath, read_file
from ...utils import get_config_files, get_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning

FILE_INDENT = ' ' * 8

IGNORE_DEFAULT_INSTANCE = {'ceph', 'dotnetclr', 'gunicorn', 'marathon', 'pgbouncer', 'process', 'supervisord'}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate default configuration files')
@click.argument('check', required=False)
def config(check):
    """Validate default configuration files."""
    if check:
        checks = [check]
    else:
        checks = sorted(get_valid_checks())

    files_failed = {}
    files_warned = {}
    num_files = 0

    echo_waiting('Validating default configuration files...')
    for check in checks:
        check_display_queue = []

        config_files = get_config_files(check)
        for config_file in config_files:
            num_files += 1
            file_display_queue = []
            file_name = basepath(config_file)
            try:
                file_data = read_file(config_file)
                config_data = yaml.safe_load(file_data)
            except Exception as e:
                files_failed[config_file] = True

                # We must convert to text here to free Exception object before it goes out of scope
                error = str(e)

                check_display_queue.append(lambda: echo_info('{}:'.format(file_name), indent=True))
                check_display_queue.append(lambda: echo_failure('Invalid YAML -', indent=FILE_INDENT))
                check_display_queue.append(lambda: echo_info(error, indent=FILE_INDENT * 2))
                continue

            errors = validate_config(file_data)
            for err in errors:
                err_msg = str(err)
                if err.severity == SEVERITY_ERROR:
                    file_display_queue.append(lambda x=err_msg: echo_failure(x, indent=FILE_INDENT))
                    files_failed[config_file] = True
                elif err.severity == SEVERITY_WARNING:
                    file_display_queue.append(lambda x=err_msg: echo_warning(x, indent=FILE_INDENT))
                    files_warned[config_file] = True
                else:
                    file_display_queue.append(lambda x=err_msg: echo_info(x, indent=FILE_INDENT))

            # Verify there is an `instances` section
            if 'instances' not in config_data:
                files_failed[config_file] = True
                file_display_queue.append(lambda: echo_failure('Missing `instances` section', indent=FILE_INDENT))

            # Verify there is a default instance
            else:
                instances = config_data['instances']
                if check not in IGNORE_DEFAULT_INSTANCE and not isinstance(instances, list):
                    files_failed[config_file] = True
                    file_display_queue.append(lambda: echo_failure('No default instance', indent=FILE_INDENT))

            if file_display_queue:
                check_display_queue.append(lambda x=file_name: echo_info('{}:'.format(x), indent=True))
                check_display_queue.extend(file_display_queue)

        if check_display_queue:
            echo_success('{}:'.format(check))
            for display in check_display_queue:
                display()

    files_failed = len(files_failed)
    files_warned = len(files_warned)
    files_passed = num_files - (files_failed + files_warned)

    if files_failed or files_warned:
        click.echo()

    if files_failed:
        echo_failure('Files with errors: {}'.format(files_failed))

    if files_warned:
        echo_warning('Files with warnings: {}'.format(files_warned))

    if files_passed:
        if files_failed or files_warned:
            echo_success('Files valid: {}'.format(files_passed))
        else:
            echo_success('All {} configuration files are valid!'.format(num_files))

    if files_failed:
        abort()
