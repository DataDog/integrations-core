# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from collections import defaultdict

from ..subprocess import run_command
from ..utils import chdir, resolve_path, stream_file_lines, write_file_lines
from .constants import REQUIREMENTS_IN, get_root

DEP_PATTERN = re.compile(r'^([^=@]+)(?:(?:==|@)([^;\s]+)(?:; *(.*))?)?')


class Package:
    """
    Structure representing a Python dependency package

    name: name of the package
    version: version of the package: 1.2.3 or a hash like efe345a21b4a for git dependencies
    marker: optional marker e.g. python_version < '3.0' or sys_platform == 'win32'
    """

    def __init__(self, name, version, marker):
        if not name:
            raise ValueError("Package must have a valid name")

        self.name = name.lower()
        self.version = version.lower() if version else ""
        self.marker = marker.lower().replace('"', "'") if marker else ""

    def __str__(self):
        version_sep = '@' if self.name.startswith('git+') else '=='
        return '{}{}{}'.format(
            self.name,
            '{}{}'.format(version_sep, self.version) if self.version else '',
            '; {}'.format(self.marker) if self.marker else '',
        )

    def __lt__(self, other):
        try:
            if self.name == other.name:
                if self.version == other.version:
                    return self.marker < other.marker
                return self.version < other.version
            return self.name < other.name
        except (AttributeError, TypeError):
            return NotImplemented

    def __gt__(self, other):
        try:
            if self.name == other.name:
                if self.version == other.version:
                    return self.marker > other.marker
                return self.version > other.version
            return self.name > other.name
        except (AttributeError, TypeError):
            return NotImplemented

    def __eq__(self, other):
        try:
            return self.name == other.name and self.version == other.version and self.marker == other.marker
        except (AttributeError, TypeError):
            return NotImplemented

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq != NotImplemented:
            return not eq
        return NotImplemented

    def __le__(self, other):
        gt = self.__gt__(other)
        if gt != NotImplemented:
            return not gt
        return NotImplemented

    def __ge__(self, other):
        lt = self.__lt__(other)
        if lt != NotImplemented:
            return not lt
        return NotImplemented

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

    @property
    def packages(self):
        return sorted(list(self._package_set))

    def get_package_versions(self, package):
        if package.name not in self._packages:
            return {}

        return self._packages[package.name].get('versions', {})

    def get_check_packages(self, check_name):
        return self._checks_deps.get(check_name, [])

    def get_package_markers(self, package):
        if package.name not in self._packages:
            return {}

        return self._packages[package.name].get('markers', {})

    def write_packages(self, reqs_file):
        """
        Dump the packages in the catalog in a requirements file
        """
        write_file_lines(reqs_file, (f'{package}\n' for package in self.packages))

    def add_package(self, check_name, package):
        """
        Add a Package to the catalog for the given check
        """
        self._package_set.add(package)
        package_data = self._packages[package.name]
        self._checks_deps[check_name].append(package)

        # Versions
        if package.version:
            versions = package_data['versions']
            versions[package.version].append(check_name)

        # Marker section
        if package.marker:
            markers = package_data['markers']
            markers[package.marker].append(check_name)


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
    """
    Generator yielding one Package instance for every corresponing line in a
    requirements file
    """
    for line in stream_file_lines(reqs_file):
        line = line.strip()
        if not line.startswith(('#', '--hash')):
            match = DEP_PATTERN.match(line)
            if match:
                package, version, marker = match.groups()
                yield Package(package.lower(), version, marker)


def make_catalog(verify=False, checks=None):
    root = get_root()
    catalog = PackageCatalog()
    errors = []
    checks = checks if checks else os.listdir(root)

    for check_name in sorted(checks):
        for package in read_packages(os.path.join(root, check_name, REQUIREMENTS_IN)):
            if not package.version:
                errors.append(f'Unpinned dependency `{package.name}` in the `{check_name}` check')
            catalog.add_package(check_name, package)

    return catalog, errors
