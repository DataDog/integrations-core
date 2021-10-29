# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ....fs import (
    chdir,
    dir_exists,
    ensure_parent_dir_exists,
    file_exists,
    path_join,
    read_file,
    read_file_lines,
    write_file_lines,
)
from ...annotations import annotate_display_queue, annotate_error
from ...configuration import ConfigSpec
from ...configuration.consumers import ModelConsumer
from ...constants import get_root
from ...manifest_utils import Manifest
from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_license_header, get_models_location, get_version_string
from ..console import CONTEXT_SETTINGS, abort, echo_debug, echo_failure, echo_info, echo_success


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate configuration data models')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.option('--sync', '-s', is_flag=True, help='Generate data models based on specifications')
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
@click.pass_context
def models(ctx, check, sync, verbose):
    """Validate configuration data models.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    root = get_root()
    community_check = ctx.obj['repo_choice'] not in ('core', 'internal')

    checks = process_checks_option(check, source='valid_checks', extend_changed=True)
    echo_info(f"Validating data models for {len(checks)} checks ...")

    specs_failed = {}
    files_failed = {}
    num_files = 0

    license_header_lines = get_license_header().splitlines(True)
    license_header_lines.append('\n')

    code_formatter = ModelConsumer.create_code_formatter()

    for check in checks:
        display_queue = {}
        if check == 'datadog_checks_base':
            spec_path = path_join(root, 'datadog_checks_base', 'tests', 'models', 'data', 'spec.yaml')
            source = 'test'
            version = '0.0.1'
        else:
            manifest = Manifest.load_manifest(check)
            if not manifest:
                echo_debug(f"Skipping validation for check: {check}; can't process manifest")
                continue
            spec_path = manifest.get_config_spec()
            if not file_exists(spec_path):
                continue

            source = check
            version = get_version_string(check)

        spec_file = read_file(spec_path)
        spec = ConfigSpec(spec_file, source=source, version=version)
        spec.load()

        if spec.errors:
            annotate_error(spec_path, '\n'.join(spec.errors))
            specs_failed[spec_path] = True
            echo_info(f'{check}:')
            for error in spec.errors:
                echo_failure(error, indent=True)
            continue

        if check == 'datadog_checks_base':
            models_location = path_join(root, 'datadog_checks_base', 'tests', 'models', 'config_models')
        else:
            models_location = get_models_location(check)

            # TODO: Remove when all integrations have models
            if not sync and not dir_exists(models_location):
                continue

        model_consumer = ModelConsumer(spec.data, code_formatter)

        # So formatters see config files
        with chdir(root):
            model_definitions = model_consumer.render()

        model_files = model_definitions.get(f'{source}.yaml')
        if not model_files:
            continue

        for model_file, (contents, errors) in model_files.items():
            check_display_queue = []
            num_files += 1

            model_file_path = path_join(models_location, model_file)
            if errors:
                files_failed[model_file_path] = True
                for error in errors:
                    check_display_queue.append((echo_failure, error))
                continue

            model_file_lines = contents.splitlines(True)
            current_model_file_lines = []
            expected_model_file_lines = []
            if file_exists(model_file_path):
                # No contents indicates a custom file
                if not contents:
                    continue

                current_model_file_lines.extend(read_file_lines(model_file_path))

                for line in current_model_file_lines:
                    if not line.startswith('#'):
                        break

                    expected_model_file_lines.append(line)

                expected_model_file_lines.extend(model_file_lines)
            else:
                if not community_check:
                    expected_model_file_lines.extend(license_header_lines)

                expected_model_file_lines.extend(model_file_lines)

            if current_model_file_lines != expected_model_file_lines:
                if sync:
                    echo_info(f'Writing data model file to `{model_file_path}`')
                    ensure_parent_dir_exists(model_file_path)
                    write_file_lines(model_file_path, expected_model_file_lines)
                else:
                    files_failed[model_file_path] = True
                    check_display_queue.append(
                        (
                            echo_failure,
                            f'File `{model_file}` is not in sync, run "ddev validate models {check} -s"',
                        )
                    )

            if not check_display_queue and verbose:
                check_display_queue.append((echo_info, f"Valid spec: {model_file}"))

            display_queue[model_file_path] = check_display_queue

        if display_queue:
            echo_info(f'{check}:')
            for model_path, queue in display_queue.items():
                annotate_display_queue(model_path, queue)
                for func, message in queue:
                    func(message, indent=True)

    specs_failed = len(specs_failed)
    files_failed = len(files_failed)
    files_passed = num_files - files_failed

    if specs_failed or files_failed:
        click.echo()

    if specs_failed:
        echo_failure(f'Specs with errors: {specs_failed}')

    if files_failed:
        echo_failure(f'Files with errors: {files_failed}')

    if files_passed:
        if specs_failed or files_failed:
            echo_success(f'Files valid: {files_passed}')
        else:
            echo_success(f'All {num_files} data model files are in sync!')

    if specs_failed or files_failed:
        abort()
