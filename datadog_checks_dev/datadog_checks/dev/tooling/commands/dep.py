# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from ...utils import write_file_lines
from ..constants import REQUIREMENTS_IN, get_agent_requirements, get_root
from ..requirements import Package, make_catalog, read_packages, resolve_requirements
from .console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning


def display_package_changes(pre_packages, post_packages, indent=''):
    """
    Print packages that've been added, removed or changed
    """
    # use package name to determine what's changed
    pre_package_names = {p.name: p for p in pre_packages}
    post_package_names = {p.name: p for p in post_packages}

    added = set(post_package_names.keys()) - set(pre_package_names.keys())
    removed = set(pre_package_names.keys()) - set(post_package_names.keys())
    changed_maybe = set(pre_package_names.keys()) & set(post_package_names.keys())

    changed = []
    for package_name in sorted(changed_maybe):
        if pre_package_names[package_name] != post_package_names[package_name]:
            changed.append((pre_package_names[package_name], post_package_names[package_name]))

    if not (added or removed or changed):
        echo_info(f'{indent}No changes')

    if added:
        echo_success(f'{indent}Added packages:')
        for package_name in sorted(added):
            echo_info(f'{indent}    {post_package_names[package_name]}')

    if removed:
        echo_failure(f'{indent}Removed packages:')
        for package_name in sorted(removed):
            echo_info(f'{indent}    {pre_package_names[package_name]}')

    if changed:
        echo_warning(f'{indent}Changed packages:')
        for pre, post in changed:
            echo_info(f'{indent}    {pre} -> {post}')


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage dependencies')
def dep():
    pass


@dep.command(context_settings=CONTEXT_SETTINGS, short_help='Resolve dependencies for any number of checks')
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
        pinned_reqs_file = os.path.join(root, check_name, REQUIREMENTS_IN)
        resolved_reqs_file = os.path.join(root, check_name, 'requirements.txt')

        if os.path.isfile(pinned_reqs_file):
            if not quiet:
                echo_info(f'Check `{check_name}`:')

            if not quiet:
                echo_waiting('    Resolving dependencies...')

            pre_packages = read_packages(resolved_reqs_file)
            result = resolve_requirements(pinned_reqs_file, resolved_reqs_file, lazy=lazy)
            if result.code:
                abort(result.stdout + result.stderr)

            if not quiet:
                post_packages = read_packages(resolved_reqs_file)
                display_package_changes(pre_packages, post_packages, indent='    ')


@dep.command(context_settings=CONTEXT_SETTINGS, short_help='Pin a dependency for all checks that require it')
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
    package_name = package.lower()
    version = version.lower()

    for check_name in sorted(os.listdir(root)):
        pinned_reqs_file = os.path.join(root, check_name, REQUIREMENTS_IN)
        resolved_reqs_file = os.path.join(root, check_name, 'requirements.txt')

        if os.path.isfile(pinned_reqs_file):
            pinned_packages = {package.name: package for package in read_packages(pinned_reqs_file)}
            if package not in pinned_packages and check_name not in checks:
                continue

            if resolving:
                pre_packages = list(read_packages(resolved_reqs_file))
            else:
                pre_packages = list(pinned_packages.values())

            if not quiet:
                echo_info(f'Check `{check_name}`:')

            if version == 'none':
                del pinned_packages[package_name]
            else:
                pinned_packages[package_name] = Package(package_name, version, marker)

            package_list = sorted(pinned_packages.values())
            write_file_lines(pinned_reqs_file, (f'{package}\n' for package in package_list))

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
    context_settings=CONTEXT_SETTINGS, short_help="Combine all dependencies for the Agent's static environment"
)
def freeze():
    """Combine all dependencies for the Agent's static environment."""
    echo_waiting('Verifying collected packages...')
    catalog, errors = make_catalog()
    if errors:
        for error in errors:
            echo_failure(error)
        abort()

    static_file = get_agent_requirements()

    echo_info(f'Static file: {static_file}')

    pre_packages = list(read_packages(static_file))

    catalog.write_packages(static_file)

    post_packages = list(read_packages(static_file))
    display_package_changes(pre_packages, post_packages)
