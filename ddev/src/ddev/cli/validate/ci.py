# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

DEFAULT_COVERAGE_THRESHOLD = 75


def code_coverage_enabled(check_name: str, app: Application) -> bool:
    if check_name in ('datadog_checks_base', 'datadog_checks_dev', 'datadog_checks_downloader', 'ddev'):
        return True

    return app.repo.integrations.get(check_name).is_agent_check


def get_coverage_sources(check_name: str, app: Application) -> list[str]:
    package_path = app.repo.integrations.get(check_name).package_directory
    package_dir = package_path.relative_to(app.repo.path)
    return sorted([f'{package_dir.as_posix()}/', f'{check_name}/tests/'])


@click.command()
@click.option('--sync', is_flag=True, help='Update the CI configuration')
@click.pass_obj
def ci(app: Application, sync: bool):
    """Validate CI infrastructure configuration."""
    import hashlib
    import json
    import re

    import yaml

    from ddev.utils.scripts.ci_matrix import construct_job_matrix, get_all_targets

    is_core = app.repo.name == 'core'
    is_marketplace = app.repo.name == 'marketplace'

    # For non-core repos, extract the workflow reference from existing workflow files
    # This allows using either @master or @<commit-sha>
    workflow_ref = 'master'  # default
    windows_workflow_ref = 'master'  # default
    if not is_core:
        jobs_workflow_path_temp = app.repo.path / '.github' / 'workflows' / 'test-all.yml'
        windows_jobs_workflow_path_temp = app.repo.path / '.github' / 'workflows' / 'test-all-windows.yml'

        # Extract reference from Linux workflow file
        if jobs_workflow_path_temp.is_file():
            existing_workflow = jobs_workflow_path_temp.read_text()
            # Look for pattern like: DataDog/integrations-core/.github/workflows/test-target.yml@<ref>
            # <ref> can be a branch name (alphanumeric + dots/dashes/underscores) or commit SHA (hex only)
            match = re.search(
                r'DataDog/integrations-core/\.github/workflows/test-target\.yml@([a-zA-Z0-9_.-]+)', existing_workflow
            )
            if match:
                workflow_ref = match.group(1)

        # Extract reference from Windows workflow file
        if windows_jobs_workflow_path_temp.is_file():
            existing_windows_workflow = windows_jobs_workflow_path_temp.read_text()
            match = re.search(
                r'DataDog/integrations-core/\.github/workflows/test-target\.yml@([a-zA-Z0-9_.-]+)',
                existing_windows_workflow,
            )
            if match:
                windows_workflow_ref = match.group(1)

    test_workflow = (
        './.github/workflows/test-target.yml'
        if app.repo.name == 'core'
        else f'DataDog/integrations-core/.github/workflows/test-target.yml@{workflow_ref}'
    )
    windows_test_workflow = (
        './.github/workflows/test-target.yml'
        if app.repo.name == 'core'
        else f'DataDog/integrations-core/.github/workflows/test-target.yml@{windows_workflow_ref}'
    )
    jobs_workflow_path = app.repo.path / '.github' / 'workflows' / 'test-all.yml'
    windows_jobs_workflow_path = app.repo.path / '.github' / 'workflows' / 'test-all-windows.yml'
    original_jobs_workflow = jobs_workflow_path.read_text() if jobs_workflow_path.is_file() else ''
    original_windows_jobs_workflow = (
        windows_jobs_workflow_path.read_text() if windows_jobs_workflow_path.is_file() else ''
    )
    ddev_jobs_id = ('jd316aba', 'j6712d43')

    job_matrix = construct_job_matrix(app.repo.path, get_all_targets(app.repo.path))

    # Reduce the target-envs to single jobs with the same name
    # We do this to keep the job list from exceeding Github's maximum file size limit
    job_dict: dict[str, dict[str, Any]] = {}
    for job in job_matrix:
        # Remove anything inside parentheses from job names and trim trailing space
        target_name = re.sub(r'\s*\(.*?\)', '', job['name']).rstrip()
        if target_name not in job_dict:
            job_dict[target_name] = job
            job_dict[target_name]['name'] = target_name
            job_dict[target_name]['target-env'] = [job['target-env']] if 'target-env' in job else []
        elif 'target-env' in job:
            job_dict[target_name]['target-env'].append(job['target-env'])
    job_matrix = list(job_dict.values())

    jobs: dict[str, dict[str, Any]] = {}
    windows_jobs: dict[str, dict[str, Any]] = {}
    for data in job_matrix:
        jobs_to_update = jobs

        if 'windows' in data['platform']:
            jobs_to_update = windows_jobs

        python_restriction = data.get('python-support', '')
        config: dict[str, Any] = {
            'job-name': data['name'],
            'target': data['target'],
            'platform': data['platform'],
            'runner': json.dumps(data['runner'], separators=(',', ':')),
            'repo': '${{ inputs.repo }}',
            'context': '${{ inputs.context }}',
            # Options
            'python-version': '${{ inputs.python-version }}',
            'latest': '${{ inputs.latest }}',
            'agent-image': '${{ inputs.agent-image }}',
            'agent-image-py2': '${{ inputs.agent-image-py2 }}',
            'agent-image-windows': '${{ inputs.agent-image-windows }}',
            'agent-image-windows-py2': '${{ inputs.agent-image-windows-py2 }}',
            'test-py2': '2' in python_restriction if python_restriction else '${{ inputs.test-py2 }}',
            'test-py3': '3' in python_restriction if python_restriction else '${{ inputs.test-py3 }}',
        }
        # We have to enforce a minimum on the number of target-envs to avoid exceeding the maximum GHA object size limit
        # This way we get the benefit of parallelization for the targets that need it most
        # The 7 here is just a magic number tuned to avoid exceeding the limit at the time of writing
        if len(data['target-env']) > 7:
            config['target-env'] = '${{ matrix.target-env }}'

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
        # Allow providing pytest arguments for core, support to run (or not run) flaky tests
        if is_core:
            config.update(
                {
                    'pytest-args': '${{ inputs.pytest-args }}',
                }
            )

        # Prevent redundant job hierarchy names at the bottom of pull requests and also satisfy the naming requirements:
        # https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_id
        #
        # We want the job ID to be unique but also small so it displays concisely on the bottom of pull requests
        job_id = hashlib.sha256(config['job-name'].encode('utf-8')).hexdigest()[:7]
        job_id = f'j{job_id}'

        # Use the appropriate workflow reference based on platform
        workflow_to_use = windows_test_workflow if 'windows' in data['platform'] else test_workflow
        job_config = {'uses': workflow_to_use, 'with': config, 'secrets': 'inherit'}
        if 'target-env' in config:
            job_config['strategy'] = {
                'matrix': {'target-env': data['target-env']},
                'fail-fast': False,
            }
        if job_id in ddev_jobs_id:
            job_config['if'] = '${{ inputs.skip-ddev-tests == false }}'
        jobs_to_update[job_id] = job_config

        if data['target'] == 'ddev':
            jobs_to_update[job_id]['if'] = '${{ inputs.skip-ddev-tests == false }}'

    jobs_component = yaml.safe_dump({'jobs': jobs}, default_flow_style=False, sort_keys=False)
    windows_jobs_component = yaml.safe_dump({'jobs': windows_jobs}, default_flow_style=False, sort_keys=False)

    # Enforce proper string types
    for field in (
        'repo',
        'python-version',
        'setup-env-vars',
        'agent-image',
        'agent-image-py2',
        'agent-image-windows',
        'agent-image-windows-py2',
        'skip-ddev-tests',
    ):
        jobs_component = jobs_component.replace(f'${{{{ inputs.{field} }}}}', f'"${{{{ inputs.{field} }}}}"')
        windows_jobs_component = windows_jobs_component.replace(
            f'${{{{ inputs.{field} }}}}', f'"${{{{ inputs.{field} }}}}"'
        )

    manual_component = original_jobs_workflow.split('jobs:')[0].strip()
    windows_manual_component = original_windows_jobs_workflow.split('jobs:')[0].strip()
    expected_jobs_workflow = f'{manual_component}\n\n{jobs_component}'
    expected_windows_jobs_workflow = f'{windows_manual_component}\n\n{windows_jobs_component}'
    target_path = app.repo.path / '.github' / 'workflows' / 'test-all.yml'
    windows_target_path = app.repo.path / '.github' / 'workflows' / 'test-all-windows.yml'

    # Check if either workflow needs updating
    workflows_need_sync = (
        original_jobs_workflow != expected_jobs_workflow
        or original_windows_jobs_workflow != expected_windows_jobs_workflow
    )

    if workflows_need_sync:
        if sync:
            if original_jobs_workflow != expected_jobs_workflow:
                target_path.write_text(expected_jobs_workflow)
            if original_windows_jobs_workflow != expected_windows_jobs_workflow:
                windows_target_path.write_text(expected_windows_jobs_workflow)
        else:
            app.abort('CI configuration is not in sync, try again with the `--sync` flag')

    validation_tracker = app.create_validation_tracker('CI configuration validation')

    repo_choice = app.repo.name
    valid_repos = ['core', 'marketplace', 'extras', 'internal']
    if repo_choice not in valid_repos:
        app.abort(f'Unknown repository `{repo_choice}`')

    if is_marketplace:
        validation_tracker.success()
        validation_tracker.display()
        return

    _validate_code_coverage(app, sync, validation_tracker, repo_choice)


def _validate_code_coverage(
    app: Application,
    sync: bool,
    validation_tracker: Any,
    repo_choice: str,
) -> None:
    import yaml

    config_filename = 'code-coverage.datadog.yml'
    config_path = app.repo.path / config_filename

    if not config_path.is_file():
        validation_tracker.error((repo_choice,), message=f'Unable to find the code coverage config file: {config_filename}')
        validation_tracker.display()
        app.abort()

    config = yaml.safe_load(config_path.read_text())
    if config is None:
        config = {}

    testable_checks = {integration.name for integration in app.repo.integrations.iter_testable('all')}
    excluded_jobs = {
        name for name, conf in app.repo.config.get('/overrides/ci', {}).items() if conf.get('exclude', False)
    }

    expected_checks = set()
    for check in testable_checks:
        if check not in excluded_jobs and code_coverage_enabled(check, app):
            expected_checks.add(check)

    existing_services = config.get('services') or []
    existing_service_ids = {s['id'] for s in existing_services if 'id' in s}

    success = True
    fixed = False
    error_message = ''

    # Validate existing services have correct paths
    for service in existing_services:
        service_id = service.get('id', '')
        if service_id not in expected_checks:
            continue

        expected_paths = get_coverage_sources(service_id, app)
        configured_paths = service.get('paths', [])
        if sorted(configured_paths) != sorted(expected_paths):
            message = f'Service `{service_id}` has incorrect coverage source paths\n'
            if sync:
                fixed = True
                service['paths'] = expected_paths
                app.display_success(f'Configured coverage paths for service `{service_id}`\n')
            else:
                success = False
                error_message += message

    missing_services = sorted(expected_checks - existing_service_ids)
    if missing_services:
        num_missing = len(missing_services)
        message = f"Code coverage config has {num_missing} missing service{'s' if num_missing > 1 else ''}\n"

        if sync:
            fixed = True
            for check_name in missing_services:
                existing_services.append({
                    'id': check_name,
                    'paths': get_coverage_sources(check_name, app),
                })
                app.display_success(f'Added service `{check_name}`\n')
        else:
            success = False
            error_message += message

    if not success:
        app.display_info('Try running `ddev validate ci --sync`\n')
        validation_tracker.error((str(config_path),), message=error_message)
        validation_tracker.display()
        app.abort()
    elif fixed:
        config['services'] = sorted(existing_services, key=lambda s: s.get('id', ''))

        # Ensure at least one gate exists
        gates = config.get('gates') or []
        if not gates:
            gates.append({
                'type': 'total_coverage_percentage',
                'config': {'threshold': DEFAULT_COVERAGE_THRESHOLD},
            })
            config['gates'] = gates
            app.display_success(f'Added default coverage gate with {DEFAULT_COVERAGE_THRESHOLD}% threshold\n')

        output = yaml.safe_dump(config, default_flow_style=False, sort_keys=False)
        config_path.write_text(output)
        app.display_success(f'Successfully fixed {config_filename}')

        validation_tracker.success()
        validation_tracker.display()
    else:
        validation_tracker.success()
        validation_tracker.display()
