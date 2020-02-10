# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import yaml

from ....utils import file_exists, path_join, read_file, write_file
from ...constants import get_root
from ...utils import get_testable_checks, load_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

REPOS = {
    'core': {
        'jobs_definition_relative_path': '.azure-pipelines/templates/test-all-checks.yml',
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
        'display_name_overrides': {},
        'ignored_missing_jobs': set(),
    },
}


def sort_jobs(jobs):
    return sorted(jobs, key=lambda job: (not job['checkName'].startswith('datadog_checks_'), job['checkName']))


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate CI infrastructure configuration')
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
@click.pass_context
def ci(ctx, fix):
    """Validate CI infrastructure configuration."""
    root = get_root()

    repo_choice = ctx.obj['repo_choice']
    if repo_choice not in REPOS:
        abort('Unknown repository `{}`'.format(repo_choice))

    repo_data = REPOS[repo_choice]

    jobs_definition_relative_path = repo_data['jobs_definition_relative_path']
    jobs_definition_path = path_join(root, *jobs_definition_relative_path.split('/'))
    if not file_exists(jobs_definition_path):
        abort('Unable to find the file defining all `master` jobs')

    jobs_definition = yaml.safe_load(read_file(jobs_definition_path))
    jobs = jobs_definition['jobs'][0]['parameters']['checks']

    testable_checks = get_testable_checks()
    defined_checks = set()
    cached_display_names = {}
    success = True
    fixed = False

    for job in jobs:
        check_name = job['checkName']
        defined_checks.add(check_name)

        if check_name not in testable_checks:
            success = False
            echo_failure('Defined check `{}` has no tox.ini file'.format(check_name))
            continue

        if check_name in cached_display_names:
            display_name = cached_display_names[check_name]
        else:
            display_name = repo_data['display_name_overrides'].get(
                check_name, load_manifest(check_name).get('display_name', check_name)
            )
            cached_display_names[check_name] = display_name

        if 'displayName' not in job:
            message = 'Job `{}` has no `displayName` attribute'.format(check_name)

            if fix:
                fixed = True
                echo_warning(message)
                job['displayName'] = display_name
                echo_success('Set `displayName` to `{}`'.format(display_name))
            else:
                success = False
                echo_failure(message)

        job_name = job['displayName']
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
                echo_failure(message)

        if 'os' not in job:
            message = 'Job `{}` has no `os` attribute'.format(check_name)

            if fix:
                fixed = True
                echo_warning(message)
                job['os'] = 'linux'
                echo_success('Set `os` to `linux`')
            else:
                success = False
                echo_failure(message)

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
                    'displayName': load_manifest(missing_check).get('display_name', missing_check),
                    'os': 'linux',
                }
                jobs.append(job)
                echo_success('Added job `{}`'.format(job['displayName']))

            jobs[:] = sort_jobs(jobs)
        else:
            success = False
            echo_failure(message)

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
                echo_failure(message)

    if not success:
        echo_info('Try running `ddev validate ci --fix`')
        abort()
    elif fixed:
        output = yaml.safe_dump(jobs_definition, default_flow_style=False, sort_keys=False)
        write_file(jobs_definition_path, output)
        echo_success('Successfully fixed {}'.format(jobs_definition_relative_path))
