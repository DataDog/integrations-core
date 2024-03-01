# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


def read_file(file, encoding='utf-8'):
    # type: (str, str) -> str
    with open(file, 'r', encoding=encoding) as f:
        return f.read()


def write_file(file, contents, encoding='utf-8'):
    with open(file, 'w', encoding=encoding) as f:
        f.write(contents)


def code_coverage_enabled(check_name, app):
    if check_name in ('datadog_checks_base', 'datadog_checks_dev', 'datadog_checks_downloader', 'ddev'):
        return True

    return app.repo.integrations.get(check_name).is_agent_check


def get_coverage_sources(check_name, app):
    package_path = app.repo.integrations.get(check_name).package_directory
    package_dir = package_path.relative_to(app.repo.path)
    return sorted([str(package_dir.as_posix()), f'{check_name}/tests'])


def sort_projects(projects):
    return sorted(projects.items(), key=lambda item: (item[0] != 'default', item[0]))


@click.command()
@click.option('--sync', is_flag=True, help='Update the CI configuration')
@click.pass_obj
def ci(app: Application, sync: bool):
    """Validate CI infrastructure configuration."""
    import hashlib
    import json
    import os
    from collections import defaultdict

    import yaml

    from ddev.utils.scripts.ci_matrix import construct_job_matrix, get_all_targets

    is_core = app.repo.name == 'core'
    is_marketplace = app.repo.name == 'marketplace'
    test_workflow = (
        './.github/workflows/test-target.yml'
        if app.repo.name == 'core'
        else 'DataDog/integrations-core/.github/workflows/test-target.yml@master'
    )
    jobs_workflow_path = app.repo.path / '.github' / 'workflows' / 'test-all.yml'
    original_jobs_workflow = jobs_workflow_path.read_text() if jobs_workflow_path.is_file() else ''

    jobs = {}
    for data in construct_job_matrix(app.repo.path, get_all_targets(app.repo.path)):
        python_restriction = data.get('python-support', '')
        config = {
            'job-name': data['name'],
            'target': data['target'],
            'platform': data['platform'],
            'runner': json.dumps(data['runner'], separators=(',', ':')),
            'repo': '${{ inputs.repo }}',
            # Options
            'python-version': '${{ inputs.python-version }}',
            'standard': '${{ inputs.standard }}',
            'latest': '${{ inputs.latest }}',
            'agent-image': '${{ inputs.agent-image }}',
            'agent-image-py2': '${{ inputs.agent-image-py2 }}',
            'agent-image-windows': '${{ inputs.agent-image-windows }}',
            'agent-image-windows-py2': '${{ inputs.agent-image-windows-py2 }}',
            'test-py2': '2' in python_restriction if python_restriction else '${{ inputs.test-py2 }}',
            'test-py3': '3' in python_restriction if python_restriction else '${{ inputs.test-py3 }}',
        }
        if is_core or is_marketplace:
            config.update(
                {
                    'minimum-base-package': '${{ inputs.minimum-base-package }}',
                }
            )

        if not is_core:
            config.update(
                {
                    'setup-env-vars': '${{ inputs.setup-env-vars }}',
                }
            )

        # Prevent redundant job hierarchy names at the bottom of pull requests and also satisfy the naming requirements:
        # https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_id
        #
        # We want the job ID to be unique but also small so it displays concisely on the bottom of pull requests
        job_id = hashlib.sha256(config['job-name'].encode('utf-8')).hexdigest()[:7]
        job_id = f'j{job_id}'

        jobs[job_id] = {'uses': test_workflow, 'with': config, 'secrets': 'inherit'}

    jobs_component = yaml.safe_dump({'jobs': jobs}, default_flow_style=False, sort_keys=False)

    # Enforce proper string types
    for field in (
        'repo',
        'python-version',
        'setup-env-vars',
        'agent-image',
        'agent-image-py2',
        'agent-image-windows',
        'agent-image-windows-py2',
    ):
        jobs_component = jobs_component.replace(f'${{{{ inputs.{field} }}}}', f'"${{{{ inputs.{field} }}}}"')

    manual_component = original_jobs_workflow.split('jobs:')[0].strip()
    expected_jobs_workflow = f'{manual_component}\n\n{jobs_component}'

    if original_jobs_workflow != expected_jobs_workflow:
        if sync:
            jobs_workflow_path.write_text(expected_jobs_workflow)
        else:
            app.abort('CI configuration is not in sync, try again with the `--sync` flag')

    validation_tracker = app.create_validation_tracker('CI configuration validation')
    error_message = ''
    warning_message = ''

    repo_choice = app.repo.name
    valid_repos = ['core', 'marketplace', 'extras', 'internal']
    if repo_choice not in valid_repos:
        app.abort(f'Unknown repository `{repo_choice}`')

    # marketplace does not have a .codecov.yml file
    if app.repo.name == 'marketplace':
        return

    testable_checks = {integration.name for integration in app.repo.integrations.iter_testable('all')}

    cached_display_names: defaultdict[str, str] = defaultdict(str)

    codecov_config_relative_path = '.codecov.yml'

    path_split = str(codecov_config_relative_path).split('/')
    codecov_config_path = os.path.join(app.repo.path, *path_split)
    if not os.path.isfile(codecov_config_path):
        error_message = 'Unable to find the Codecov config file'
        validation_tracker.error((repo_choice,), message=error_message)
        validation_tracker.display()
        app.abort()

    codecov_config = yaml.safe_load(read_file(codecov_config_path))
    projects = codecov_config.setdefault('coverage', {}).setdefault('status', {}).setdefault('project', {})
    defined_checks = set()
    success = True
    fixed = False

    for project, data in list(projects.items()):
        if project == 'default':
            continue

        project_flags = data.get('flags', [])
        if len(project_flags) != 1:
            success = False
            error_message += f'Project `{project}` must have exactly one flag\n'
            continue

        check_name = project_flags[0]

        if check_name in defined_checks:
            success = False
            error_message += f'Check `{check_name}` is defined as a flag in more than one project\n'
            continue

        defined_checks.add(check_name)
        # Project names cannot contain spaces, see:
        # https://github.com/DataDog/integrations-core/pull/6760#issuecomment-634976885
        if check_name in cached_display_names:
            display_name = cached_display_names[check_name].replace(' ', '_')
        else:
            try:
                integration = app.repo.integrations.get(check_name)
            except OSError as e:
                if str(e).startswith('Integration does not exist: '):
                    continue

                raise

            display_name = integration.display_name
            display_name = display_name.replace(' ', '_')
            cached_display_names[check_name] = display_name

        if project != display_name:
            message = f'Project `{project}` should be called `{display_name}`\n'

            if sync:
                fixed = True
                warning_message += message
                if display_name not in projects:
                    projects[display_name] = data
                    del projects[project]
                app.display_success(f'Renamed project to `{display_name}`\n')
            else:
                success = False
                error_message += message

    # This works because we ensure there is a 1 to 1 correspondence between projects and checks (flags)
    excluded_jobs = {
        name for name, config in app.repo.config.get('/overrides/ci', {}).items() if config.get('exclude', False)
    }
    missing_projects = testable_checks - set(defined_checks) - excluded_jobs

    not_agent_checks = set()
    for check in set(missing_projects):
        if not code_coverage_enabled(check, app):
            not_agent_checks.add(check)
            missing_projects.discard(check)

    if missing_projects:
        num_missing_projects = len(missing_projects)
        message = (
            f"Codecov config has {num_missing_projects} missing project{'s' if num_missing_projects > 1 else ''}\n"
        )

        if sync:
            fixed = True
            warning_message += message

            for missing_check in sorted(missing_projects):
                display_name = app.repo.integrations.get(missing_check).display_name
                display_name = display_name.replace(' ', '_')
                projects[display_name] = {'target': 75, 'flags': [missing_check]}
                app.display_success(f'Added project `{display_name}`\n')
        else:
            success = False
            error_message += message

    flags = codecov_config.setdefault('flags', {})
    defined_checks = set()

    for flag, data in list(flags.items()):
        defined_checks.add(flag)

        expected_coverage_paths = get_coverage_sources(flag, app)

        configured_coverage_paths = data.get('paths', [])
        if configured_coverage_paths != expected_coverage_paths:
            message = f'Flag `{flag}` has incorrect coverage source paths\n'

            if sync:
                fixed = True
                warning_message += message
                data['paths'] = expected_coverage_paths
                app.display_success(f'Configured coverage paths for flag `{flag}`\n')
            else:
                success = False
                error_message += message

        if not data.get('carryforward'):
            message = f'Flag `{flag}` must have carryforward set to true\n'

            if sync:
                fixed = True
                warning_message += message
                data['carryforward'] = True
                app.display_success(f'Enabled the carryforward feature for flag `{flag}`\n')
            else:
                success = False
                error_message += message

    missing_flags = testable_checks - set(defined_checks) - excluded_jobs
    for check in set(missing_flags):
        if check in not_agent_checks or not code_coverage_enabled(check, app):
            missing_flags.discard(check)

    if missing_flags:
        num_missing_flags = len(missing_flags)
        message = f"Codecov config has {num_missing_flags} missing flag{'s' if num_missing_flags > 1 else ''}\n"

        if sync:
            fixed = True
            warning_message += message

            for missing_check in sorted(missing_flags):
                flags[missing_check] = {'carryforward': True, 'paths': get_coverage_sources(missing_check, app)}
                app.display_success(f'Added flag `{missing_check}`\n')
        else:
            success = False
            error_message += message

    if not success:
        message = 'Try running `ddev validate ci --sync`\n'
        app.display_info(message)
        validation_tracker.error((codecov_config_path,), message=error_message)

        validation_tracker.display()
        app.abort()
    elif fixed:
        codecov_config['coverage']['status']['project'] = dict(sort_projects(projects))
        codecov_config['flags'] = dict(sorted(flags.items()))
        output = yaml.safe_dump(codecov_config, default_flow_style=False, sort_keys=False)
        write_file(codecov_config_path, output)
        app.display_success(f'Successfully fixed {codecov_config_relative_path}')

        validation_tracker.success()
        validation_tracker.display()
    else:
        validation_tracker.success()
        validation_tracker.display()
