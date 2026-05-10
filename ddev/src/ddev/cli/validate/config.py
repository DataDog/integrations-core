# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import difflib
import os
import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.integration.core import Integration

DEFAULT_INDENT = ' ' * 4
FILE_INDENT = ' ' * 8

IGNORE_DEFAULT_INSTANCE = {'ceph', 'dotnetclr', 'gunicorn', 'marathon', 'pgbouncer', 'process', 'supervisord'}

CONFIGLESS_CHECKS = {
    'ddev',
    'datadog_checks_dev',
    'datadog_checks_base',
    'datadog_checks_dependency_provider',
    'datadog_checks_downloader',
}


def _validate_default_template(spec_file: str) -> bool:
    if 'template: init_config' not in spec_file or 'template: instances' not in spec_file:
        return True

    templates = {
        'intances': [f'template: init_config/{t}' for t in ['default', 'openmetrics_legacy', 'openmetrics', 'jmx']],
        'init_config': [f'template: init_config/{t}' for t in ['default', 'openmetrics_legacy', 'openmetrics', 'jmx']],
    }
    return all(any(re.search(t, spec_file) for t in tpls) for tpls in templates)


def _data_directory(app: Application, check_name: str):
    """Return the directory where rendered example files live for the given check name."""
    if check_name == 'agent':
        return app.repo.path / 'pkg' / 'config'
    return app.repo.path / check_name / 'datadog_checks' / check_name / 'data'


def _spec_file_path(app: Application, check_name: str):
    if check_name == 'agent':
        return app.repo.path / 'pkg' / 'config' / 'spec.yaml'
    return app.repo.path / check_name / 'assets' / 'configuration' / 'spec.yaml'


def _check_version(integration: Integration | None, check_name: str) -> str | None:
    """Return the version string used as a default in the spec, mirroring legacy behaviour."""
    if check_name == 'agent':
        return None
    if integration is None:
        return None
    about_file = integration.package_directory / '__about__.py'
    if not about_file.is_file():
        return None
    match = re.search(r'^__version__ *= *(?:[\'"])(.+?)(?:[\'"])', about_file.read_text(), re.MULTILINE)
    return match.group(1) if match else None


def _legacy_config_files(app: Application, check_name: str) -> list:
    """Return any legacy free-form config files that exist for the check."""
    if check_name == 'agent':
        config_template = app.repo.path / 'pkg' / 'config' / 'config_template.yaml'
        return [config_template] if config_template.is_file() else []

    if check_name in CONFIGLESS_CHECKS:
        return []

    data_dir = app.repo.path / check_name / 'datadog_checks' / check_name / 'data'
    candidates = [
        data_dir / 'auto_conf.yaml',
        data_dir / 'conf.yaml.default',
        data_dir / 'conf.yaml.example',
    ]
    return sorted([path for path in candidates if path.is_file()])


def _validate_config_legacy(
    app: Application,
    check_name: str,
    check_display_queue: list,
    files_failed: dict,
    files_warned: dict,
    file_counter: list,
) -> None:
    import yaml

    from ddev.validation.config_spec.validator import validate_config as validate_config_yaml
    from ddev.validation.config_spec.validator_errors import SEVERITY_ERROR, SEVERITY_WARNING

    for config_file in _legacy_config_files(app, check_name):
        file_counter.append(None)
        file_name = config_file.name
        try:
            file_data = config_file.read_text()
            config_data = yaml.safe_load(file_data)
        except Exception as e:
            files_failed[str(config_file)] = True
            error = str(e)

            check_display_queue.append(lambda file_name=file_name: app.display_info(f'{file_name}:', indent=DEFAULT_INDENT))
            check_display_queue.append(lambda: app.display_error('Invalid YAML -', indent=FILE_INDENT))
            check_display_queue.append(lambda error=error: app.display_info(error, indent=FILE_INDENT * 2))
            continue

        file_display_queue = []
        errors = validate_config_yaml(file_data)
        for err in errors:
            err_msg = str(err)
            if err.severity == SEVERITY_ERROR:
                file_display_queue.append(lambda x=err_msg: app.display_error(x, indent=FILE_INDENT))
                files_failed[str(config_file)] = True
            elif err.severity == SEVERITY_WARNING:
                file_display_queue.append(lambda x=err_msg: app.display_warning(x, indent=FILE_INDENT))
                files_warned[str(config_file)] = True
            else:
                file_display_queue.append(lambda x=err_msg: app.display_info(x, indent=FILE_INDENT))

        if 'instances' not in (config_data or {}):
            files_failed[str(config_file)] = True
            message = 'Missing `instances` section'
            file_display_queue.append(lambda message=message: app.display_error(message, indent=FILE_INDENT))
        else:
            instances = config_data['instances']
            if check_name not in IGNORE_DEFAULT_INSTANCE and not isinstance(instances, list):
                files_failed[str(config_file)] = True
                message = 'No default instance'
                file_display_queue.append(lambda message=message: app.display_error(message, indent=FILE_INDENT))

        if file_display_queue:
            check_display_queue.append(lambda x=file_name: app.display_info(f'{x}:', indent=DEFAULT_INDENT))
            check_display_queue.extend(file_display_queue)


def _iter_target_checks(app: Application, check: str | None) -> list[str]:
    """Resolve the user input into the list of check names to validate, mirroring legacy semantics."""
    if app.repo.name == 'agent':
        return ['agent']

    selection: tuple[str, ...]
    if check is None or check.lower() == 'all':
        selection = ()
        names = sorted({integration.name for integration in app.repo.integrations.iter_all(selection)})
    elif check.lower() == 'changed':
        changed = sorted({integration.name for integration in app.repo.integrations.iter_changed_code()})
        valid = {integration.name for integration in app.repo.integrations.iter_all(())}
        names = [name for name in changed if name in valid]
        if 'datadog_checks_dev' in names or 'datadog_checks_base' in names:
            names = sorted(valid)
    else:
        names = [check]

    return names


@click.command(short_help='Validate default configuration files')
@click.argument('check', required=False)
@click.option('--sync', '-s', is_flag=True, help='Generate example configuration files based on specifications')
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
@click.pass_context
def config(ctx: click.Context, check: str | None, sync: bool, verbose: bool) -> None:
    """Validate default configuration files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    from ddev.validation.configuration import ConfigSpec
    from ddev.validation.configuration.consumers import ExampleConsumer

    app: Application = ctx.obj
    checks = _iter_target_checks(app, check)
    is_core_check = app.repo.name == 'core'

    files_failed: dict = {}
    files_warned: dict = {}
    file_counter: list = []

    app.display_waiting(f'Validating default configuration files for {len(checks)} checks...')
    for check_name in checks:
        if check_name in CONFIGLESS_CHECKS:
            app.display_info(f'Skipping {check_name}, it does not need an Agent-level config.')
            continue

        check_display_queue: list = []

        spec_file_path = _spec_file_path(app, check_name)
        if not spec_file_path.is_file():
            example_location = _data_directory(app, check_name)

            # If there's an example file in core and no spec file, we should fail
            if is_core_check and example_location.is_dir() and len(os.listdir(example_location)) > 0:
                file_counter.append(None)
                files_failed[str(spec_file_path)] = True

            check_display_queue.append(
                lambda spec_file_path=spec_file_path, check_name=check_name: app.display_error(
                    f"Did not find spec file {spec_file_path} for check {check_name}"
                )
            )

            _validate_config_legacy(app, check_name, check_display_queue, files_failed, files_warned, file_counter)
            if verbose:
                check_display_queue.append(lambda: app.display_warning('No spec found', indent=DEFAULT_INDENT))
            if check_display_queue:
                app.display_info(f'{check_name}:')
            for display in check_display_queue:
                display()
            continue

        file_counter.append(None)

        if check_name == 'agent':
            source = 'datadog'
            integration = None
        else:
            source = check_name
            try:
                integration = app.repo.integrations.get(check_name)
            except OSError:
                integration = None
        version = _check_version(integration, check_name)

        spec_file_content = spec_file_path.read_text()

        if not _validate_default_template(spec_file_content):
            message = "Missing default template in init_config or instances section"
            files_failed[str(spec_file_path)] = True
            check_display_queue.append(lambda message=message, **kwargs: app.display_error(message, **kwargs))

        spec = ConfigSpec(spec_file_content, source=source, version=version)
        spec.load()
        if spec.errors:
            files_failed[str(spec_file_path)] = True
            for error in spec.errors:
                check_display_queue.append(lambda error=error, **kwargs: app.display_error(error, **kwargs))
        else:
            example_location = _data_directory(app, check_name)
            example_consumer = ExampleConsumer(spec.data)
            for example_file, (contents, errors) in example_consumer.render().items():
                file_counter.append(None)
                example_file_path = example_location / example_file
                if errors:
                    files_failed[str(example_file_path)] = True
                    for error in errors:
                        check_display_queue.append(lambda error=error, **kwargs: app.display_error(error, **kwargs))
                else:
                    if not example_file_path.is_file() or example_file_path.read_text() != contents:
                        if sync:
                            app.display_info(f"Writing config file to `{example_file_path}`")
                            example_file_path.parent.mkdir(parents=True, exist_ok=True)
                            example_file_path.write_text(contents)
                        else:
                            files_failed[str(example_file_path)] = True
                            message = (
                                f'File `{example_file}` is not in sync, run "ddev validate config {check_name} -s"'
                            )
                            if example_file_path.is_file():
                                current_file = example_file_path.read_text()
                                for diff_line in difflib.context_diff(
                                    current_file.splitlines(), contents.splitlines(), "current", "expected"
                                ):
                                    message += f'\n{diff_line}'
                            check_display_queue.append(
                                lambda message=message, **kwargs: app.display_error(message, **kwargs)
                            )

        if check_display_queue or verbose:
            app.display_info(f'{check_name}:')
            if verbose:
                check_display_queue.append(lambda **kwargs: app.display_info('Valid spec', **kwargs))
            for display in check_display_queue:
                display(indent=DEFAULT_INDENT)

    num_files = len(file_counter)
    files_failed_count = len(files_failed)
    files_warned_count = len(files_warned)
    files_passed = num_files - (files_failed_count + files_warned_count)

    if files_failed_count or files_warned_count:
        click.echo()

    if files_failed_count:
        app.display_error(f'Files with errors: {files_failed_count}')

    if files_warned_count:
        app.display_warning(f'Files with warnings: {files_warned_count}')

    if files_passed:
        if files_failed_count or files_warned_count:
            app.display_success(f'Files valid: {files_passed}')
        else:
            app.display_success(f'All {num_files} configuration files are valid!')

    if files_failed_count:
        app.abort()
