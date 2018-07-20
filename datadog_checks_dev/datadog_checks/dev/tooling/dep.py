# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from collections import defaultdict, namedtuple

from .constants import get_root
from ..subprocess import run_command
from ..utils import (
    chdir, resolve_path, stream_file_lines, write_file_lines
)

DEP_PATTERN = re.compile(r'([^=]+)(?:==([^;\s]+)(?:; *(.*))?)?')
Package = namedtuple('Package', ('name', 'version', 'marker'))


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
                package, version, marker = match.groups()

                if version:
                    version = version.lower()
                else:
                    version = None

                if marker:
                    marker = marker.lower().replace('"', "'")
                else:
                    marker = None

                yield Package(package.lower(), version, marker)


def write_packages(packages, reqs_file):
    write_file_lines(
        reqs_file,
        ('{}\n'.format(format_package(package)) for package in sorted(packages))
    )


def format_package(package):
    return '{}{}{}'.format(
        package.name,
        '=={}'.format(package.version) if package.version else '',
        '; {}'.format(package.marker) if package.marker else ''
    )


def collect_packages(verify=False, checks=None):
    root = get_root()
    checks = checks if checks else os.listdir(root)
    packages = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    errors = []

    for check_name in sorted(checks):
        for package in read_packages(os.path.join(root, check_name, 'requirements.in')):
            package_data = packages[package.name]

            # Versions
            if verify and package.version is None:
                errors.append('Unpinned dependency `{}` in the `{}` check.'.format(package.name, check_name))

            versions = package_data['versions']
            versions[package.version].append(check_name)

            if verify and len(versions) > 1:
                errors.append(
                    'Multiple dependency versions for `{}` in the {} and {} checks.'.format(
                        package.name, versions.popitem()[1], versions.popitem()[1]
                    )
                )

            # Marker section
            markers = package_data['markers']
            markers[package.marker].append(check_name)

            if verify and len(markers) > 1:
                errors.append(
                    'Multiple environment marker definitions for `{}` in the {} and {} checks.'.format(
                        package.name, versions.popitem()[1], versions.popitem()[1]
                    )
                )

    return packages, errors
