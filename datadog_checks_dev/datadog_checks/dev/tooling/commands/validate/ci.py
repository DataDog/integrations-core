# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import yaml

from ....fs import file_exists, path_join, read_file, write_file
from ...annotations import annotate_display_queue, annotate_error
from ...constants import get_root
from ...testing import coverage_sources
from ...utils import code_coverage_enabled, get_testable_checks, load_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

REPOS = {
    'core': {
        'jobs_definition_relative_path': '.azure-pipelines/templates/test-all-checks.yml',
        'codecov_config_relative_path': '.codecov.yml',
        'display_name_overrides': {
            'datadog_checks_base': 'Datadog Checks Base',
            'datadog_checks_dev': 'Datadog Checks Dev',
            'datadog_checks_downloader': 'Datadog Checks Downloader',
            'ecs_fargate': 'Amazon ECS Fargate',
            'kube_scheduler': 'Kubernetes Scheduler',
            'nfsstat': 'NFSstat',
            'nginx': 'NGINX',
            'nginx_ingress_controller': 'NGINX Ingress Controller',
            'openstack_controller': 'OpenStack Controller',
            'teamcity': 'TeamCity',
        },
        'ignored_missing_jobs': {'hyperv'},
    },
    'extras': {
        'jobs_definition_relative_path': '.azure-pipelines/all.yml',
        'codecov_config_relative_path': '.codecov.yml',
        'display_name_overrides': {
            'contrastsecurity': 'Contrast Security',
            'gnatsd_streaming': 'Gnatsd Streaming',
            'reboot_required': 'Reboot Required',
            'storm': 'Storm',
        },
        'ignored_missing_jobs': set(),
    },
    'internal': {
        'jobs_definition_relative_path': '.azure-pipelines/all.yml',
        'codecov_config_relative_path': '.codecov.yml',
        'display_name_overrides': {},
        'ignored_missing_jobs': set(),
    },
    'marketplace': {
        'jobs_definition_relative_path': '.azure-pipelines/all.yml',
        'display_name_overrides': {},
        'codecov_config_relative_path': '',
        'ignored_missing_jobs': set(),
    },
}


def sort_jobs(jobs):
    return sorted(
        jobs,
        key=lambda job: (
            not job.get('checkName', '').startswith('datadog_checks_'),
            get_attribute_from_job(job, 'checkName'),
        ),
    )


def sort_projects(projects):
    return sorted(projects.items(), key=lambda item: (item[0] != 'default', item[0]))


def get_coverage_sources(check_name):
    package_dir, tests_dir = coverage_sources(check_name)
    return sorted([f'{check_name}/{package_dir}', f'{check_name}/{tests_dir}'])


def get_attribute_from_job(job, attribute):
    value = job.get(attribute)
    if not value:
        # Probably a nested block using an AZP template variable:
        # - ${{ if ... }}:
        #    - checkName: ...
        job = list(job.values())[0][0]
        value = job.get(attribute)
    return value


def validate_master_jobs(fix, repo_data, testable_checks, cached_display_names):
    display_queue = []
    jobs_definition_relative_path = repo_data['jobs_definition_relative_path']
    if not jobs_definition_relative_path:
        echo_info("Skipping since jobs path isn't defined")
        return

    jobs_definition_path = path_join(get_root(), *jobs_definition_relative_path.split('/'))
    if not file_exists(jobs_definition_path):
        abort('Unable to find the file defining all `master` jobs')

    jobs_definition = yaml.safe_load(read_file(jobs_definition_path))
    jobs = jobs_definition['jobs'][0]['parameters']['checks']

    defined_checks = set()
    success = True
    fixed = False

    for job in jobs:
        check_name = get_attribute_from_job(job, 'checkName')
        defined_checks.add(check_name)

        if check_name not in testable_checks:
            success = False
            message = 'Defined check `{}` has no tox.ini file'.format(check_name)
            annotate_error(jobs_definition_path, message)
            continue

        if check_name in cached_display_names:
            display_name = cached_display_names[check_name]
        else:
            display_name = repo_data['display_name_overrides'].get(
                check_name, load_manifest(check_name).get('display_name', check_name)
            )
            cached_display_names[check_name] = display_name

        job_name = get_attribute_from_job(job, 'displayName')
        if not job_name:
            message = 'Job `{}` has no `displayName` attribute'.format(check_name)

            if fix:
                fixed = True
                echo_warning(message)
                job['displayName'] = display_name
                echo_success('Set `displayName` to `{}`'.format(display_name))
            else:
                success = False
                display_queue.append((echo_failure, message))

        if not job_name.startswith(display_name):
            message = 'Job `{}` has an incorrect `displayName` ({}), it should be `{}`'.format(
                check_name, job_name, display_name
            )

            if fix:
                fixed = True
                echo_warning(message)
                job['displayName'] = display_name
                echo_success('Set `displayName` to `{}`'.format(display_name))
            else:
                success = False
                display_queue.append((echo_failure, message))

        if not get_attribute_from_job(job, 'os'):
            message = 'Job `{}` has no `os` attribute'.format(check_name)

            if fix:
                fixed = True
                echo_warning(message)
                job['os'] = 'linux'
                echo_success('Set `os` to `linux`')
            else:
                success = False
                display_queue.append((echo_failure, message))

    missing_checks = testable_checks - defined_checks - repo_data['ignored_missing_jobs']
    if missing_checks:
        num_missing_checks = len(missing_checks)
        message = 'Job definition has {} missing job{}'.format(
            num_missing_checks, 's' if num_missing_checks > 1 else ''
        )

        if fix:
            fixed = True
            echo_warning(message)

            for missing_check in sorted(missing_checks):
                job = {
                    'checkName': missing_check,
                    'displayName': repo_data['display_name_overrides'].get(
                        missing_check, load_manifest(missing_check).get('display_name', missing_check)
                    ),
                    'os': 'linux',
                }
                jobs.append(job)
                echo_success('Added job `{}`'.format(job['displayName']))

            jobs[:] = sort_jobs(jobs)
        else:
            success = False
            display_queue.append((echo_failure, message))

    if not (missing_checks and fix):
        sorted_jobs = sort_jobs(jobs)

        if jobs != sorted_jobs:
            message = 'Jobs are not sorted'

            if fix:
                fixed = True
                echo_warning(message)
                jobs[:] = sort_jobs(jobs)
                echo_success('Sorted all jobs')
            else:
                success = False
                display_queue.append((echo_failure, message))

    if not success:
        message = 'Try running `ddev validate ci --fix`'
        echo_info(message)
        display_queue.append((echo_failure, message))
        for func, message in display_queue:
            func(message)
        annotate_display_queue(jobs_definition_path, display_queue)
        abort()
    elif fixed:
        output = yaml.safe_dump(jobs_definition, default_flow_style=False, sort_keys=False)
        write_file(jobs_definition_path, output)
        echo_success('Successfully fixed {}'.format(jobs_definition_relative_path))


def validate_coverage_flags(fix, repo_data, testable_checks, cached_display_names):
    codecov_config_relative_path = repo_data['codecov_config_relative_path']
    if not codecov_config_relative_path:
        echo_info("Skipping since codecov path isn't defined")
        return

    codecov_config_path = path_join(get_root(), *codecov_config_relative_path.split('/'))
    if not file_exists(codecov_config_path):
        abort('Unable to find the Codecov config file')

    codecov_config = yaml.safe_load(read_file(codecov_config_path))
    projects = codecov_config.setdefault('coverage', {}).setdefault('status', {}).setdefault('project', {})

    defined_checks = set()
    success = True
    fixed = False
    display_queue = []

    for project, data in list(projects.items()):
        if project == 'default':
            continue

        project_flags = data.get('flags', [])
        if len(project_flags) != 1:
            success = False
            message = f'Project `{project}` must have exactly one flag'
            echo_failure(message)
            annotate_error(codecov_config_path, message)
            continue

        check_name = project_flags[0]
        if check_name in defined_checks:
            success = False
            message = f'Check `{check_name}` is defined as a flag in more than one project'
            echo_failure(message)
            annotate_error(codecov_config_path, message)
            continue

        defined_checks.add(check_name)

        if check_name not in testable_checks:
            success = False
            message = f'Defined project `{check_name}` has no tox.ini file'
            echo_failure(codecov_config_path, message)
            continue

        # Project names cannot contain spaces, see:
        # https://github.com/DataDog/integrations-core/pull/6760#issuecomment-634976885
        if check_name in cached_display_names:
            display_name = cached_display_names[check_name].replace(' ', '_')
        else:
            display_name = repo_data['display_name_overrides'].get(
                check_name, load_manifest(check_name).get('display_name', check_name)
            )
            display_name = display_name.replace(' ', '_')
            cached_display_names[check_name] = display_name

        if project != display_name:
            message = f'Project `{project}` should be called `{display_name}`'

            if fix:
                fixed = True
                echo_warning(message)
                if display_name not in projects:
                    projects[display_name] = data
                    del projects[project]
                echo_success(f'Renamed project to `{display_name}`')
            else:
                success = False
                display_queue.append((echo_failure, message))

    # This works because we ensure there is a 1 to 1 correspondence between projects and checks (flags)
    missing_projects = testable_checks - defined_checks - repo_data['ignored_missing_jobs']

    not_agent_checks = set()
    for check in set(missing_projects):
        if not code_coverage_enabled(check):
            not_agent_checks.add(check)
            missing_projects.discard(check)

    if missing_projects:
        num_missing_projects = len(missing_projects)
        message = f"Codecov config has {num_missing_projects} missing project{'s' if num_missing_projects > 1 else ''}"

        if fix:
            fixed = True
            echo_warning(message)

            for missing_check in sorted(missing_projects):
                display_name = repo_data['display_name_overrides'].get(
                    missing_check, load_manifest(missing_check).get('display_name', missing_check)
                )
                projects[display_name] = {'target': 75, 'flags': [missing_check]}
                echo_success(f'Added project `{display_name}`')
        else:
            success = False
            display_queue.append((echo_failure, message))

    flags = codecov_config.setdefault('flags', {})
    defined_checks = set()

    for flag, data in list(flags.items()):
        defined_checks.add(flag)

        if flag not in testable_checks:
            success = False
            message = f'Defined check `{flag}` has no tox.ini file'
            echo_failure(message)
            annotate_error(codecov_config_path, message)
            continue

        expected_coverage_paths = get_coverage_sources(flag)

        configured_coverage_paths = data.get('paths', [])
        if configured_coverage_paths != expected_coverage_paths:
            message = f'Flag `{flag}` has incorrect coverage source paths'

            if fix:
                fixed = True
                echo_warning(message)
                data['paths'] = expected_coverage_paths
                echo_success(f'Configured coverage paths for flag `{flag}`')
            else:
                success = False
                display_queue.append((echo_failure, message))

        if not data.get('carryforward'):
            message = f'Flag `{flag}` must have carryforward set to true'

            if fix:
                fixed = True
                echo_warning(message)
                data['carryforward'] = True
                echo_success(f'Enabled the carryforward feature for flag `{flag}`')
            else:
                success = False
                display_queue.append((echo_failure, message))

    missing_flags = testable_checks - defined_checks - repo_data['ignored_missing_jobs']
    for check in set(missing_flags):
        if check in not_agent_checks or not code_coverage_enabled(check):
            missing_flags.discard(check)

    if missing_flags:
        num_missing_flags = len(missing_flags)
        message = f"Codecov config has {num_missing_flags} missing flag{'s' if num_missing_flags > 1 else ''}"

        if fix:
            fixed = True
            echo_warning(message)

            for missing_check in sorted(missing_flags):
                flags[missing_check] = {'carryforward': True, 'paths': get_coverage_sources(missing_check)}
                echo_success(f'Added flag `{missing_check}`')
        else:
            success = False
            display_queue.append((echo_failure, message))

    if not success:
        message = 'Try running `ddev validate ci --fix`'
        display_queue.append((echo_info, message))
        annotate_display_queue(codecov_config_path, display_queue)
        for func, message in display_queue:
            func(message)
        abort()
    elif fixed:
        codecov_config['coverage']['status']['project'] = dict(sort_projects(projects))
        codecov_config['flags'] = dict(sorted(flags.items()))
        output = yaml.safe_dump(codecov_config, default_flow_style=False, sort_keys=False)
        write_file(codecov_config_path, output)
        echo_success(f'Successfully fixed {codecov_config_relative_path}')


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate CI infrastructure configuration')
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
@click.pass_context
def ci(ctx, fix):
    """Validate CI infrastructure configuration."""
    repo_choice = ctx.obj['repo_choice']
    if repo_choice not in REPOS:
        abort('Unknown repository `{}`'.format(repo_choice))

    repo_data = REPOS[repo_choice]
    testable_checks = get_testable_checks()
    cached_display_names = {}

    echo_info("Validating CI Configuration...")
    validate_master_jobs(fix, repo_data, testable_checks, cached_display_names)
    echo_success("Success", nl=True)

    echo_info("Validating Code Coverage Configuration...")
    validate_coverage_flags(fix, repo_data, testable_checks, cached_display_names)
    echo_success("Success", nl=True)
