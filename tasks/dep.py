# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os
import re
import subprocess
from collections import defaultdict
from io import open

from colorama import Fore, Style, init
from invoke import task
from invoke.exceptions import Exit
from six import iteritems

from .constants import ROOT
from .utils.common import chdir

init(autoreset=True)


DEP_PATTERN = re.compile(r'^([^=#]+)(?:==(\S+))?')


def ensure_deps_declared(compiled_reqs_file, pinned_reqs_file):
    if os.path.isfile(compiled_reqs_file) and not os.path.isfile(pinned_reqs_file):
        declacred_lines = []

        with open(compiled_reqs_file, 'r', encoding='utf-8') as f:
            for line in f:
                match = DEP_PATTERN.match(line.strip())
                if match:
                    declacred_lines.append(match.group(0) + '\n')

        with open(pinned_reqs_file, 'w', encoding='utf-8') as f:
            f.writelines(declacred_lines)


def compile_requirements(pinned_file, compiled_file, upgrade=False):
    command = ['pip-compile', '--generate-hashes', '--output-file']
    if upgrade:
        command.insert(1, '--upgrade')

    pinned_file = os.path.realpath(pinned_file)
    compiled_file = os.path.realpath(compiled_file)

    pin_dir, pinned_file = os.path.split(pinned_file)
    if not pin_dir:
        pin_dir = os.getcwd()

    command.append(os.path.relpath(compiled_file, start=pin_dir).replace('\\', '/'))
    command.append(pinned_file)

    with chdir(pin_dir):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.poll():
            raise subprocess.CalledProcessError('{}\n{}\n'.format(stdout, stderr))


def read_packages(reqs_file):
    if os.path.isfile(reqs_file):
        with open(reqs_file, 'r', encoding='utf-8') as f:
            for line in f:
                match = DEP_PATTERN.match(line.strip())
                if match:
                    yield match.groups()


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

            versions = packages[package.lower()]
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

    pinned_reqs_file = os.path.join(ROOT, 'datadog_checks_base', 'requirements.in')
    compiled_reqs_file = os.path.join(ROOT, 'datadog_checks_base', 'requirements.txt')

    pre_compiled_packages = dict(read_packages(compiled_reqs_file))
    pre_packages_set = set(pre_compiled_packages)

    pinned_lines = [
        '{}=={}\n'.format(package, versions.keys()[0])
        for package, versions in sorted(iteritems(pinned_packages))
    ]
    with open(pinned_reqs_file, 'w', encoding='utf-8') as f:
        f.writelines(pinned_lines)

    print('{}{}Resolving dependencies...'.format(Fore.MAGENTA, Style.BRIGHT))
    compile_requirements(pinned_reqs_file, compiled_reqs_file, upgrade=upgrade)

    post_compiled_packages = dict(read_packages(compiled_reqs_file))
    post_packages_set = set(post_compiled_packages)

    added = post_packages_set - pre_packages_set
    removed = pre_packages_set - post_packages_set
    changed = {
        package for package in pre_packages_set & post_packages_set
        if pre_compiled_packages[package] != post_compiled_packages[package]
    }

    if added:
        print('{}{}Added packages:'.format(Fore.CYAN, Style.BRIGHT))
        for package in sorted(added):
            print('{}    {}=={}'.format(Style.BRIGHT, package, post_compiled_packages[package]))

    if removed:
        print('{}{}Removed packages:'.format(Fore.RED, Style.BRIGHT))
        for package in sorted(removed):
            print('{}    {}=={}'.format(Style.BRIGHT, package, pre_compiled_packages[package]))

    if changed:
        print('{}{}Changed packages:'.format(Fore.YELLOW, Style.BRIGHT))
        for package in sorted(changed):
            print('{}    {}=={} -> {}=={}'.format(
                Style.BRIGHT,
                package,
                pre_compiled_packages[package],
                package,
                post_compiled_packages[package])
            )


@task
def dep_check(ctx):
    all_packages = collect_packages(verify=False)

    output = ''
    for package, versions in sorted(iteritems(all_packages)):
        if len(versions) > 1:
            output += '{}{}Multiple versions found for package `{}`:\n'.format(Fore.RED, Style.BRIGHT, package)
            for version, checks in sorted(iteritems(versions)):
                if len(checks) == 1:
                    output += '{}    {}: {}\n'.format(Style.BRIGHT, version, checks[0])
                elif len(checks) == 2:
                    output += '{}    {}: {} and {}\n'.format(Style.BRIGHT, version, checks[0], checks[1])
                else:
                    remaining = len(checks) - 2
                    output += '{}    {}: {}, {}, and {} other{}\n'.format(
                        Style.BRIGHT,
                        version,
                        checks[0],
                        checks[1],
                        remaining,
                        's' if remaining > 1 else ''
                    )
        else:
            version, checks = versions.items()[0]
            if version is None:
                output += (
                    '{}{}Unpinned dependency `{}` in the `{}` check.\n'
                    ''.format(Fore.RED, Style.BRIGHT, package, checks[0])
                )

    if output:
        print(output[:-1])
        raise Exit(1)


@task(help={
    'package': 'The package to pin throughout the checks',
    'version': 'The version of the package to pin',
    'upgrade': 'Attempt to upgrade transient dependencies',
    'quiet': 'Whether or not to hide output',
})
def dep_pin(ctx, package, version, upgrade=False, quiet=False):
    """Pin a dependency for all checks that require it.
    ``pip-compile`` must be in PATH.

    Example invocation:
        inv pin requests 2.19.1
    """
    if not (package and version):
        raise Exit('`package` and `version` are required arguments.')

    for check_name in sorted(os.listdir(ROOT)):
        check_dir = os.path.join(ROOT, check_name)
        pinned_reqs_file = os.path.join(check_dir, 'requirements.in')
        compiled_reqs_file = os.path.join(check_dir, 'requirements.txt')

        ensure_deps_declared(compiled_reqs_file, pinned_reqs_file)

        if os.path.isfile(pinned_reqs_file):
            with open(pinned_reqs_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                try:
                    pkg = line.split('=')[0].strip()
                    if pkg == package:
                        break
                except IndexError:
                    continue
            # Skip integrations that don't require the package.
            else:
                continue

            if not quiet:
                print('{}{}Check `{}`:'.format(Fore.CYAN, Style.BRIGHT, check_name))
                print('{}      Old: `{}`'.format(Style.BRIGHT, lines[i].strip()))

            lines[i] = '{}=={}\n'.format(package, version)

            with open(pinned_reqs_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            if not quiet:
                print('{}      New: `{}`'.format(Style.BRIGHT, lines[i].strip()))
                print('{}{}      Resolving dependencies...'.format(Fore.MAGENTA, Style.BRIGHT))

            compile_requirements(pinned_reqs_file, compiled_reqs_file, upgrade=upgrade)
