# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from collections import defaultdict

from six import iteritems

from .constants import get_root
from ..utils import (
    chdir, file_exists, resolve_path, run_command, stream_file_lines, write_file_lines
)

DEP_PATTERN = re.compile(r'([^=]+)(?:==(\S+))?')


def ensure_deps_declared(resolved_reqs_file, pinned_reqs_file):
    if file_exists(resolved_reqs_file) and not file_exists(pinned_reqs_file):
        resolved_packages = dict(read_packages(resolved_reqs_file))
        write_packages(resolved_packages, pinned_reqs_file)


def resolve_requirements(pinned_file, resolved_file, lazy=True):
    command = ['pip-compile', '--generate-hashes', '--output-file']
    if not lazy:
        command.insert(1, '--upgrade')

    pinned_file = resolve_path(pinned_file)
    resolved_file = resolve_path(resolved_file)

    pin_dir, pinned_file = os.path.split(pinned_file)
    if not pin_dir:
        pin_dir = os.getcwd()

    command.append(os.path.relpath(resolved_file, start=pin_dir).replace('\\', '/'))
    command.append(pinned_file)

    with chdir(pin_dir):
        return run_command(command, capture=True)


def read_packages(reqs_file):
    for line in stream_file_lines(reqs_file):
        line = line.strip()
        if not line.startswith(('#', '--hash')):
            match = DEP_PATTERN.match(line)
            if match:
                package, version = match.groups()
                yield package.lower(), version.lower()


def write_packages(packages, reqs_file):
    write_file_lines(
        reqs_file,
        (
            '{}=={}\n'.format(package, version)
            for package, version in sorted(iteritems(packages))
        )
    )


def collect_packages(verify=False, checks=None):
    root = get_root()
    checks = checks if checks else os.listdir(root)
    packages = defaultdict(lambda: defaultdict(list))
    errors = []

    for check_name in sorted(checks):
        for package, version in read_packages(os.path.join(root, check_name, 'requirements.in')):
            if verify and version is None:
                errors.append('Unpinned dependency `{}` in the `{}` check.'.format(package, check_name))

            versions = packages[package]
            versions[version].append(check_name)

            if verify and len(versions) > 1:
                errors.append(
                    'Multiple dependency versions for `{}` in the {} and {} checks.'.format(
                        package, versions.popitem()[1], versions.popitem()[1]
                    )
                )

    return packages, errors
