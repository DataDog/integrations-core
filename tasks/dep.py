# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import print_function, unicode_literals

import os
import re
import subprocess
import sys
from collections import defaultdict
from io import open

from colorama import Fore, Style, init
from invoke import task
from invoke.exceptions import Exit
from six import iteritems

from .constants import ROOT
from .utils.common import chdir

init(autoreset=True)


DEP_PATTERN = re.compile(r'([^=]+)(?:==(\S+))?')


def ensure_deps_declared(resolved_reqs_file, pinned_reqs_file):
    if os.path.isfile(resolved_reqs_file) and not os.path.isfile(pinned_reqs_file):
        resolved_packages = dict(read_packages(resolved_reqs_file))
        write_packages(resolved_packages, pinned_reqs_file)


def resolve_requirements(pinned_file, resolved_file, upgrade=False):
    command = ['pip-compile', '--generate-hashes', '--output-file']
    if upgrade:
        command.insert(1, '--upgrade')

    pinned_file = os.path.realpath(pinned_file)
    resolved_file = os.path.realpath(resolved_file)

    pin_dir, pinned_file = os.path.split(pinned_file)
    if not pin_dir:
        pin_dir = os.getcwd()

    command.append(os.path.relpath(resolved_file, start=pin_dir).replace('\\', '/'))
    command.append(pinned_file)

    with chdir(pin_dir):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.poll():
            sys.exit('{}\n{}\n'.format(stdout.decode('utf-8'), stderr.decode('utf-8')))


def read_packages(reqs_file):
    if os.path.isfile(reqs_file):
        with open(reqs_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line.startswith(('#', '--hash')):
                    match = DEP_PATTERN.match(line)
                    if match:
                        package, version = match.groups()
                        yield package.lower(), version


def write_packages(packages, reqs_file):
    with open(reqs_file, 'w', encoding='utf-8') as f:
        f.writelines(
            '{}=={}\n'.format(package, version)
            for package, version in sorted(iteritems(packages))
        )


def print_package_changes(pre_packages, post_packages, indent=''):
    pre_packages_set = set(pre_packages)
    post_packages_set = set(post_packages)

    added = post_packages_set - pre_packages_set
    removed = pre_packages_set - post_packages_set
    changed = {
        package for package in pre_packages_set & post_packages_set
        if pre_packages[package] != post_packages[package]
    }

    if added:
        print('{}{}{}Added packages:'.format(Fore.CYAN, Style.BRIGHT, indent))
        for package in sorted(added):
            print('{}{}    {}=={}'.format(Style.BRIGHT, indent, package, post_packages[package]))

    if removed:
        print('{}{}{}Removed packages:'.format(Fore.RED, Style.BRIGHT, indent))
        for package in sorted(removed):
            print('{}{}    {}=={}'.format(Style.BRIGHT, indent, package, pre_packages[package]))

    if changed:
        print('{}{}{}Changed packages:'.format(Fore.YELLOW, Style.BRIGHT, indent))
        for package in sorted(changed):
            print('{}{}    {}=={} -> {}=={}'.format(
                Style.BRIGHT,
                indent,
                package,
                pre_packages[package],
                package,
                post_packages[package])
            )

    if not (added or removed or changed):
        print('{}{}No changes'.format(Style.BRIGHT, indent))


def collect_packages(verify=True, checks=None):
    checks = checks if checks else os.listdir(ROOT)
    packages = defaultdict(lambda: defaultdict(list))

    for check_name in sorted(checks):
        for package, version in read_packages(os.path.join(ROOT, check_name, 'requirements.in')):
            if verify and version is None:
                raise Exit(
                    '{}{}Unpinned dependency `{}` in the `{}` check.'.format(
                        Fore.RED, Style.BRIGHT, package, check_name
                    )
                )

            versions = packages[package]
            versions[version].append(check_name)

            if verify and len(versions) > 1:
                raise Exit(
                    '{}{}Multiple dependency versions for `{}` in the {} and {} checks.'.format(
                        Fore.RED, Style.BRIGHT, package, versions.popitem()[1], versions.popitem()[1]
                    )
                )

    return packages


@task
def dep_freeze(ctx, upgrade=False):
    pinned_packages = collect_packages()

    pinned_reqs_file = os.path.join(ROOT, 'datadog_checks_base', 'agent_requirements.in')
    resolved_reqs_file = os.path.join(ROOT, 'datadog_checks_base', 'agent_requirements.txt')

    pre_resolved_packages = dict(read_packages(resolved_reqs_file))

    pinned_lines = [
        '{}=={}\n'.format(package, versions.keys()[0])
        for package, versions in sorted(iteritems(pinned_packages))
    ]
    with open(pinned_reqs_file, 'w', encoding='utf-8') as f:
        f.writelines(pinned_lines)

    print('{}{}Resolving dependencies...'.format(Fore.MAGENTA, Style.BRIGHT))
    resolve_requirements(pinned_reqs_file, resolved_reqs_file, upgrade=upgrade)

    post_resolved_packages = dict(read_packages(resolved_reqs_file))
    print_package_changes(pre_resolved_packages, post_resolved_packages)


@task
def dep_check(ctx):
    all_packages = collect_packages(verify=False)

    output_lines = []
    for package, versions in sorted(iteritems(all_packages)):
        if len(versions) > 1:
            output_lines.append(
                '{}{}Multiple versions found for package `{}`:'.format(Fore.RED, Style.BRIGHT, package)
            )
            for version, checks in sorted(iteritems(versions)):
                if len(checks) == 1:
                    output_lines.append('{}    {}: {}'.format(Style.BRIGHT, version, checks[0]))
                elif len(checks) == 2:
                    output_lines.append('{}    {}: {} and {}'.format(Style.BRIGHT, version, checks[0], checks[1]))
                else:
                    remaining = len(checks) - 2
                    output_lines.append('{}    {}: {}, {}, and {} other{}'.format(
                        Style.BRIGHT,
                        version,
                        checks[0],
                        checks[1],
                        remaining,
                        's' if remaining > 1 else ''
                    ))
        else:
            version, checks = versions.items()[0]
            if version is None:
                output_lines.append((
                    '{}{}Unpinned dependency `{}` in the `{}` check.'
                    ''.format(Fore.RED, Style.BRIGHT, package, checks[0])
                ))

    if output_lines:
        for line in output_lines:
            print(line)
        raise Exit(1)


@task(help={
    'package': 'The package to pin throughout the checks',
    'version': 'The version of the package to pin',
    'upgrade': 'When resolving, attempt to upgrade transient dependencies',
    'quiet': 'Whether or not to hide output',
})
def dep_pin(ctx, package, version, upgrade=False, quiet=False):
    """Pin a dependency for all checks that require it. Setting the version
    to `none` will remove the package. `pip-compile` must be in PATH if
    resolving; disable resolving via `--no-resolve`.

    Example invocations:
        inv pin cryptography 2.2.2
        inv pin --upgrade requests 2.19.1
        inv pin scandir none
    """
    if not (package and version):
        raise Exit('`package` and `version` are required arguments.')

    package = package.lower()

    for check_name in sorted(os.listdir(ROOT)):
        check_dir = os.path.join(ROOT, check_name)
        pinned_reqs_file = os.path.join(check_dir, 'requirements.in')
        resolved_reqs_file = os.path.join(check_dir, 'requirements.txt')

        ensure_deps_declared(resolved_reqs_file, pinned_reqs_file)

        if os.path.isfile(pinned_reqs_file):
            pinned_packages = dict(read_packages(pinned_reqs_file))
            if package not in pinned_packages:
                continue

            if not quiet:
                print('{}Check `{}`:'.format(Style.BRIGHT, check_name))

            if version.lower() == 'none':
                del pinned_packages[package]
            else:
                pinned_packages[package] = version

            write_packages(pinned_packages, pinned_reqs_file)

            if not quiet:
                print('{}{}    Resolving dependencies...'.format(Fore.MAGENTA, Style.BRIGHT))

            pre_packages = dict(read_packages(resolved_reqs_file))
            resolve_requirements(pinned_reqs_file, resolved_reqs_file, upgrade=upgrade)

            if not quiet:
                post_packages = dict(read_packages(resolved_reqs_file))
                print_package_changes(pre_packages, post_packages, indent='    ')
