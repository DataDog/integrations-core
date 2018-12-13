# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from collections import defaultdict

from .constants import get_root
from ..subprocess import run_command
from ..utils import (
    chdir, resolve_path, stream_file_lines, write_file_lines
)

DEP_PATTERN = re.compile(r'([^=]+)(?:==([^;\s]+)(?:; *(.*))?)?')


class Package:
    def __init__(self, name, version, marker):
        self.name = name
        self.version = version
        self.marker = marker

    def __str__(self):
        return '{}{}{}'.format(
            self.name,
            '=={}'.format(self.version) if self.version else '',
            '; {}'.format(self.marker) if self.marker else ''
        )

    def __lt__(self, other):
        if self.name < other.name:
            return True
        elif self.version < other.version:
            return True
        else:
            return self.marker < other.marker

    def __eq__(self, other):
        return (
            self.name == other.name and
            self.version == other.version and
            self.marker == other.marker
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.name, self.version, self.marker))


class PackageCatalog:
    def __init__(self):
        """
        self._packages has this format:
        {
            '<package_name>': {
                'versions': {
                    '<version_number_1>': ['<a_check_name>'],
                    '<version_number_2>': ['<another_check_name'>],
                },
                'markers': {
                    '<marker_1>': ['<a_check_name>'],
                    '<marker_2>': ['<another_check_name'>],
                }
            },
        }
        """
        self._packages = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self._checks_deps = defaultdict(list)
        self._package_set = set()
        self._errors = []

    @property
    def errors(self):
        return self._errors

    @property
    def packages(self):
        return sorted(list(self._package_set))

    def get_package_versions(self, package):
        if package.name not in self._packages:
            return {}

        return self._packages[package.name].get('versions')

    def get_check_packages(self, check_name):
        return self._checks_deps.get(check_name, [])

    def get_package_markers(self, package):
        if package.name not in self._packages:
            return {}

        return self._packages[package.name].get('markers')

    def write_packages(self, reqs_file):
        """
        Dump the packages in the catalog in a requirements file
        """
        write_file_lines(reqs_file, ('{}\n'.format(package) for package in sorted(self._package_set)))

    def add_package(self, check_name, package):
        """
        Add a Package to the catalog for the given check
        """
        self._package_set.add(package)
        package_data = self._packages[package.name]
        self._checks_deps[check_name].append(package)

        # Versions
        if package.version is None:
            self._errors.append('Unpinned dependency `{}` in the `{}` check.'.format(package.name, check_name))
        else:
            versions = package_data['versions']
            versions[package.version].append(check_name)
            if len(versions) > 1:
                self._errors.append(
                    'Multiple dependency versions for `{}` in the {} and {} checks.'.format(
                        package.name, versions.popitem()[1], versions.popitem()[1]
                    )
                )

        # Marker section
        markers = package_data['markers']
        markers[package.marker].append(check_name)

        if len(markers) > 1:
            self._errors.append(
                'Multiple environment marker definitions for `{}` in the {} and {} checks.'.format(
                    package.name, versions.popitem()[1], versions.popitem()[1]
                )
            )


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


def collect_packages(verify=False, checks=None):
    root = get_root()
    catalog = PackageCatalog()
    checks = checks if checks else os.listdir(root)

    for check_name in sorted(checks):
        for package in read_packages(os.path.join(root, check_name, 'requirements.in')):
            catalog.add_package(check_name, package)

    return catalog
