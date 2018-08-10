# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from six import iteritems, itervalues

from .utils import (
    CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning
)
from ..constants import get_root
from ..dep import (
    Package, collect_packages, format_package, read_packages, resolve_requirements, write_packages
)
from ...utils import get_next


def transform_package_data(packages):
    return {package.name: package for package in packages}


def display_package_changes(pre_packages, post_packages, indent=''):
    pre_packages = transform_package_data(pre_packages)
    post_packages = transform_package_data(post_packages)
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
            echo_info('{}    {}'.format(indent, format_package(post_packages[package])))

    if removed:
        echo_failure('{}Removed packages:'.format(indent))
        for package in sorted(removed):
            echo_info('{}    {}'.format(indent, format_package(pre_packages[package])))

    if changed:
        echo_warning('{}Changed packages:'.format(indent))
        for package in sorted(changed):
            echo_info('{}    {} -> {}'.format(
                indent,
                format_package(pre_packages[package]),
                format_package(post_packages[package])
            ))


def display_multiple_attributes(attributes, message):
    echo_failure(message)
    for attribute, checks in sorted(iteritems(attributes)):
        if len(checks) == 1:
            echo_info('    {}: {}'.format(attribute, checks[0]))
        elif len(checks) == 2:
            echo_info('    {}: {} and {}'.format(attribute, checks[0], checks[1]))
        else:
            remaining = len(checks) - 2
            echo_info('    {}: {}, {}, and {} other{}'.format(
                attribute,
                checks[0],
                checks[1],
                remaining,
                's' if remaining > 1 else ''
            ))


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

    for package, package_data in sorted(iteritems(all_packages)):
        versions = package_data['versions']
        if len(versions) > 1:
            failed = True
            display_multiple_attributes(versions, 'Multiple versions found for package `{}`:'.format(package))
        else:
            version, checks = get_next(iteritems(versions))
            if version is None:
                failed = True
                echo_failure('Unpinned dependency `{}` in the `{}` check.'.format(package, checks[0]))

        markers = package_data['markers']
        if len(markers) > 1:
            failed = True
            display_multiple_attributes(markers, 'Multiple markers found for package `{}`:'.format(package))

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

        if os.path.isfile(pinned_reqs_file):
            if not quiet:
                echo_info('Check `{}`:'.format(check_name))

            if not quiet:
                echo_waiting('    Resolving dependencies...')

            pre_packages = read_packages(resolved_reqs_file)
            result = resolve_requirements(pinned_reqs_file, resolved_reqs_file, lazy=lazy)
            if result.code:
                abort(result.stdout + result.stderr)

            if not quiet:
                post_packages = read_packages(resolved_reqs_file)
                display_package_changes(pre_packages, post_packages, indent='    ')


@dep.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Pin a dependency for all checks that require it'
)
@click.argument('package')
@click.argument('version')
@click.argument('checks', nargs=-1)
@click.option('--marker', '-m', help='Environment marker to use')
@click.option('--resolve', '-r', 'resolving', is_flag=True, help='Resolve transient dependencies')
@click.option('--lazy', '-l', is_flag=True, help='Do not attempt to upgrade transient dependencies when resolving')
@click.option('--quiet', '-q', is_flag=True)
def pin(package, version, checks, marker, resolving, lazy, quiet):
    """Pin a dependency for all checks that require it. This can
    also resolve transient dependencies.

    Setting the version to `none` will remove the package. You can
    specify an unlimited number of additional checks to apply the
    pin for via arguments.
    """
    root = get_root()
    package = package.lower()
    version = version.lower()

    for check_name in sorted(os.listdir(root)):
        pinned_reqs_file = os.path.join(root, check_name, 'requirements.in')
        resolved_reqs_file = os.path.join(root, check_name, 'requirements.txt')

        if os.path.isfile(pinned_reqs_file):
            pinned_packages = transform_package_data(read_packages(pinned_reqs_file))
            if package not in pinned_packages and check_name not in checks:
                continue

            if resolving:
                pre_packages = list(read_packages(resolved_reqs_file))
            else:
                pre_packages = list(itervalues(pinned_packages))

            if not quiet:
                echo_info('Check `{}`:'.format(check_name))

            if version == 'none':
                del pinned_packages[package]
            else:
                pinned_packages[package] = Package(package, version, marker)

            write_packages(itervalues(pinned_packages), pinned_reqs_file)

            if not quiet:
                echo_waiting('    Resolving dependencies...')

            if resolving:
                result = resolve_requirements(pinned_reqs_file, resolved_reqs_file, lazy=lazy)
                if result.code:
                    abort(result.stdout + result.stderr)

            if not quiet:
                post_packages = read_packages(resolved_reqs_file if resolving else pinned_reqs_file)
                display_package_changes(pre_packages, post_packages, indent='    ')


@dep.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Combine all dependencies for the Agent's static environment"
)
def freeze():
    """Combine all dependencies for the Agent's static environment."""
    echo_waiting('Verifying collected packages...')
    pinned_packages, errors = collect_packages(verify=True)
    if errors:
        abort(errors[0])

    root = get_root()
    static_file = os.path.join(
        root, 'datadog_checks_base', 'datadog_checks', 'data', 'agent_requirements.in'
    )

    echo_info('Static file: {}'.format(static_file))

    pre_packages = list(read_packages(static_file))

    write_packages(
        (
            Package(package, get_next(data['versions']), get_next(data['markers']))
            for package, data in sorted(iteritems(pinned_packages))
        ),
        static_file
    )

    post_packages = list(read_packages(static_file))
    display_package_changes(pre_packages, post_packages)
