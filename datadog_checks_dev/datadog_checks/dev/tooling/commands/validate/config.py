# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import yaml

from datadog_checks.dev.tooling.config_validator.validator import validate_config
from datadog_checks.dev.tooling.config_validator.validator_errors import SEVERITY_ERROR, SEVERITY_WARNING
from datadog_checks.dev.tooling.specs.configuration import ConfigSpec
from datadog_checks.dev.tooling.specs.configuration.consumers import ExampleConsumer

from ....fs import basepath, file_exists, path_join, read_file, write_file
from ...testing import process_checks_option
from ...utils import (
    complete_valid_checks,
    get_config_files,
    get_config_spec,
    get_data_directory,
    get_version_string,
    load_manifest,
)
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning

FILE_INDENT = ' ' * 8

IGNORE_DEFAULT_INSTANCE = {'ceph', 'dotnetclr', 'gunicorn', 'marathon', 'pgbouncer', 'process', 'supervisord'}

TEMPLATES = ['default', 'openmetrics_legacy', 'openmetrics', 'jmx']


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate default configuration files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.option('--sync', '-s', is_flag=True, help='Generate example configuration files based on specifications')
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
@click.pass_context
def config(ctx, check, sync, verbose):
    """Validate default configuration files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """

    repo_choice = ctx.obj['repo_choice']
    if repo_choice == 'agent':
        checks = ['agent']
    else:
        checks = process_checks_option(check, source='valid_checks')

    files_failed = {}
    files_warned = {}
    file_counter = []

    echo_waiting(f'Validating default configuration files for {len(checks)} checks...')
    for check in checks:
        check_display_queue = []

        spec_path = get_config_spec(check)
        if not file_exists(spec_path):
            validate_config_legacy(check, check_display_queue, files_failed, files_warned, file_counter)
            if verbose:
                check_display_queue.append(lambda: echo_warning('No spec found', indent=True))
            if check_display_queue:
                echo_info(f'{check}:')
            for display in check_display_queue:
                display()
            continue

        file_counter.append(None)

        # source is the default file name
        if check == 'agent':
            display_name = 'Datadog Agent'
            source = 'datadog'
            version = None
        else:
            display_name = load_manifest(check).get('display_name', check)
            source = check
            version = get_version_string(check)

        spec_file = read_file(spec_path)
        default_temp = validate_default_template(spec_file)
        spec = ConfigSpec(spec_file, source=source, version=version)
        spec.load()

        if not default_temp:
            check_display_queue.append(
                lambda **kwargs: echo_failure("Missing default template in init_config or instances section")
            )

        if spec.errors:
            files_failed[spec_path] = True
            for error in spec.errors:
                check_display_queue.append(lambda error=error, **kwargs: echo_failure(error, **kwargs))
        else:
            if spec.data['name'] != display_name:
                files_failed[spec_path] = True
                check_display_queue.append(
                    lambda **kwargs: echo_failure(
                        f"Spec  name `{spec.data['name']}` should be `{display_name}`", **kwargs
                    )
                )

            example_location = get_data_directory(check)
            example_consumer = ExampleConsumer(spec.data)
            for example_file, (contents, errors) in example_consumer.render().items():
                file_counter.append(None)
                example_file_path = path_join(example_location, example_file)
                if errors:
                    files_failed[example_file_path] = True
                    for error in errors:
                        check_display_queue.append(lambda error=error, **kwargs: echo_failure(error, **kwargs))
                else:
                    if not file_exists(example_file_path) or read_file(example_file_path) != contents:
                        if sync:
                            echo_info(f"Writing config file to `{example_file_path}`")
                            write_file(example_file_path, contents)
                        else:
                            files_failed[example_file_path] = True
                            check_display_queue.append(
                                lambda example_file=example_file, **kwargs: echo_failure(
                                    f'File `{example_file}` is not in sync, run "ddev validate config -s"', **kwargs
                                )
                            )

        if check_display_queue or verbose:
            echo_info(f'{check}:')
            if verbose:
                check_display_queue.append(lambda **kwargs: echo_info('Valid spec', **kwargs))
            for display in check_display_queue:
                display(indent=True)

    num_files = len(file_counter)
    files_failed = len(files_failed)
    files_warned = len(files_warned)
    files_passed = num_files - (files_failed + files_warned)

    if files_failed or files_warned:
        click.echo()

    if files_failed:
        echo_failure(f'Files with errors: {files_failed}')

    if files_warned:
        echo_warning(f'Files with warnings: {files_warned}')

    if files_passed:
        if files_failed or files_warned:
            echo_success(f'Files valid: {files_passed}')
        else:
            echo_success(f'All {num_files} configuration files are valid!')

    if files_failed:
        abort()


def validate_default_template(spec_file):
    init_config_default = False
    instances_default = False
    if 'template: init_config' not in spec_file or 'template: instances' not in spec_file:
        # This config spec does not have init_config or instances
        return True

    for line in spec_file.split('\n'):
        if any("init_config/{}".format(template) in line for template in TEMPLATES):
            init_config_default = True
        if any("instances/{}".format(template) in line for template in TEMPLATES):
            instances_default = True

        if instances_default and init_config_default:
            return True
    return False


def validate_config_legacy(check, check_display_queue, files_failed, files_warned, file_counter):
    config_files = get_config_files(check)
    for config_file in config_files:
        file_counter.append(None)
        file_name = basepath(config_file)
        try:
            file_data = read_file(config_file)
            config_data = yaml.safe_load(file_data)
        except Exception as e:
            files_failed[config_file] = True

            # We must convert to text here to free Exception object before it goes out of scope
            error = str(e)

            check_display_queue.append(lambda: echo_info(f'{file_name}:', indent=True))
            check_display_queue.append(lambda: echo_failure('Invalid YAML -', indent=FILE_INDENT))
            check_display_queue.append(lambda: echo_info(error, indent=FILE_INDENT * 2))
            continue

        file_display_queue = []
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
            check_display_queue.append(lambda x=file_name: echo_info(f'{x}:', indent=True))
            check_display_queue.extend(file_display_queue)
