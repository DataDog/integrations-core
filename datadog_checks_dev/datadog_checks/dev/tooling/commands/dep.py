# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from six import iteritems

from .utils import (
    CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning
)
from ..constants import get_root
from ..dep import (
    collect_packages, ensure_deps_declared, read_packages, resolve_requirements, write_packages
)
from ...utils import get_next, write_file_lines


def display_package_changes(pre_packages, post_packages, indent=''):
    pre_packages_set = set(pre_packages)
    post_packages_set = set(post_packages)

    added = post_packages_set - pre_packages_set
    removed = pre_packages_set - post_packages_set
    changed = {
        package for package in pre_packages_set & post_packages_set
        if pre_packages[package] != post_packages[package]
    }

    if not (added or removed or changed):
        echo_info('{}No changes'.format(indent))

    if added:
        echo_success('{}Added packages:'.format(indent))
        for package in sorted(added):
            echo_info('{}    {}=={}'.format(indent, package, post_packages[package]))

    if removed:
        echo_failure('{}Removed packages:'.format(indent))
        for package in sorted(removed):
            echo_info('{}    {}=={}'.format(indent, package, pre_packages[package]))

    if changed:
        echo_warning('{}Changed packages:'.format(indent))
        for package in sorted(changed):
            echo_info('{}    {}=={} -> {}=={}'.format(
                indent,
                package,
                pre_packages[package],
                package,
                post_packages[package])
            )


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage dependencies')
def dep():
    pass


@dep.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Verify the uniqueness of dependency versions across all checks'
)
def verify():
    """Verify the uniqueness of dependency versions across all checks."""
    all_packages, _ = collect_packages()
    failed = False

    for package, versions in sorted(iteritems(all_packages)):
        if len(versions) > 1:
            failed = True
            echo_failure('Multiple versions found for package `{}`:'.format(package))
            for version, checks in sorted(iteritems(versions)):
                if len(checks) == 1:
                    echo_info('    {}: {}'.format(version, checks[0]))
                elif len(checks) == 2:
                    echo_info('    {}: {} and {}'.format(version, checks[0], checks[1]))
                else:
                    remaining = len(checks) - 2
                    echo_info('    {}: {}, {}, and {} other{}'.format(
                        version,
                        checks[0],
                        checks[1],
                        remaining,
                        's' if remaining > 1 else ''
                    ))
        else:
            version, checks = get_next(iteritems(versions))
            if version is None:
                failed = True
                echo_failure('Unpinned dependency `{}` in the `{}` check.'.format(package, checks[0]))

    if failed:
        abort()


@dep.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Resolve dependencies for any number of checks'
)
@click.argument('checks', nargs=-1, required=True)
@click.option('--lazy', '-l', is_flag=True, help='Do not attempt to upgrade transient dependencies')
@click.option('--quiet', '-q', is_flag=True)
def resolve(checks, lazy, quiet):
    """Resolve transient dependencies for any number of checks.
    If you want to do this en masse, put `all`.
    """
    root = get_root()
    if 'all' in checks:
        checks = os.listdir(root)

    for check_name in sorted(checks):
        pinned_reqs_file = os.path.join(root, check_name, 'requirements.in')
        resolved_reqs_file = os.path.join(root, check_name, 'requirements.txt')

        ensure_deps_declared(resolved_reqs_file, pinned_reqs_file)

        if os.path.isfile(pinned_reqs_file):
            if not quiet:
                echo_info('Check `{}`:'.format(check_name))

            if not quiet:
                echo_waiting('    Resolving dependencies...')

            pre_packages = dict(read_packages(resolved_reqs_file))
            result = resolve_requirements(pinned_reqs_file, resolved_reqs_file, lazy=lazy)
            if result.code:
                abort(result.stdout + result.stderr)

            if not quiet:
                post_packages = dict(read_packages(resolved_reqs_file))
                display_package_changes(pre_packages, post_packages, indent='    ')


@dep.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Pin a dependency for all checks that require it'
)
@click.argument('package')
@click.argument('version')
@click.argument('checks', nargs=-1)
@click.option('--lazy', '-l', is_flag=True, help='Do not attempt to upgrade transient dependencies')
@click.option('--quiet', '-q', is_flag=True)
def pin(package, version, checks, lazy, quiet):
    """Pin a dependency for all checks that require it. This will
    also resolve transient dependencies.

    Setting the version to `none` will remove the package. You can
    specify an unlimited number of additional checks to apply the
    pin for via arguments.
    """
    root = get_root()
    package = package.lower()

    for check_name in sorted(os.listdir(root)):
        pinned_reqs_file = os.path.join(root, check_name, 'requirements.in')
        resolved_reqs_file = os.path.join(root, check_name, 'requirements.txt')

        ensure_deps_declared(resolved_reqs_file, pinned_reqs_file)

        if os.path.isfile(pinned_reqs_file):
            pinned_packages = dict(read_packages(pinned_reqs_file))
            if package not in pinned_packages and check_name not in checks:
                continue

            if not quiet:
                echo_info('Check `{}`:'.format(check_name))

            if version.lower() == 'none':
                del pinned_packages[package]
            else:
                pinned_packages[package] = version

            write_packages(pinned_packages, pinned_reqs_file)

            if not quiet:
                echo_waiting('    Resolving dependencies...')

            pre_packages = dict(read_packages(resolved_reqs_file))
            result = resolve_requirements(pinned_reqs_file, resolved_reqs_file, lazy=lazy)
            if result.code:
                abort(result.stdout + result.stderr)

            if not quiet:
                post_packages = dict(read_packages(resolved_reqs_file))
                display_package_changes(pre_packages, post_packages, indent='    ')


@dep.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Combine all dependencies for the Agent's static environment"
)
@click.option('--lazy', '-l', is_flag=True, help='Do not attempt to upgrade transient dependencies')
def freeze(lazy):
    """Combine all dependencies for the Agent's static environment."""
    echo_waiting('Verifying collected packages...')
    pinned_packages, errors = collect_packages(verify=True)
    if errors:
        abort(errors[0])

    root = get_root()
    pinned_reqs_file = os.path.join(root, 'datadog_checks_base', 'agent_requirements.in')
    resolved_reqs_file = os.path.join(root, 'datadog_checks_base', 'agent_requirements.txt')

    echo_info('Pinned file: {}'.format(pinned_reqs_file))
    echo_info('Resolved file: {}'.format(resolved_reqs_file))

    pre_resolved_packages = dict(read_packages(resolved_reqs_file))

    pinned_lines = [
        '{}=={}\n'.format(package, get_next(versions))
        for package, versions in sorted(iteritems(pinned_packages))
    ]
    write_file_lines(pinned_reqs_file, pinned_lines)

    echo_waiting('Resolving dependencies...')
    result = resolve_requirements(pinned_reqs_file, resolved_reqs_file, lazy=lazy)
    if result.code:
        abort(result.stdout + result.stderr)

    post_resolved_packages = dict(read_packages(resolved_reqs_file))
    display_package_changes(pre_resolved_packages, post_resolved_packages)
