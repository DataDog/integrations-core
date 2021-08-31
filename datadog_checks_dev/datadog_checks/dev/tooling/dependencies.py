import os
from collections import defaultdict

from packaging.requirements import InvalidRequirement, Requirement

from ..fs import stream_file_lines
from .constants import get_agent_requirements, get_root
from .utils import get_valid_checks


class DependencyDefinition:
    __slots__ = ('name', 'requirement', 'file_path', 'line_number', 'check_name')

    def __init__(self, name, requirement, file_path, line_number, check_name=None):
        self.name = name
        self.requirement = requirement
        self.file_path = file_path
        self.line_number = line_number
        self.check_name = check_name

    def __repr__(self):
        return f'<DependencyDefinition name={self.name} check_name={self.check_name} requirement={self.requirement}'

    @property
    def _normalized_marker(self):
        if self.requirement.marker is None:
            return self.requirement.marker

        new_marker = str(self.requirement.marker).strip()
        new_marker = new_marker.replace('\'', "\"")
        return new_marker

    def same_name_marker(self, other):
        return self.name == other.name and self._normalized_marker == other._normalized_marker


def create_dependency_data():
    return defaultdict(lambda: defaultdict(lambda: []))


def load_dependency_data(req_file, dependencies, errors, check_name=None):
    for i, line in enumerate(stream_file_lines(req_file)):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        try:
            req = Requirement(line)
        except InvalidRequirement as e:
            errors.append(f'File `{req_file}` has an invalid dependency: `{line}`\n{e}')
            continue

        name = req.name.lower().replace('_', '-')
        dependency = dependencies[name][req.specifier]
        dependency.append(DependencyDefinition(name, req, req_file, i, check_name))


def load_base_check(req_file, dependencies, errors, check_name=None):
    for i, line in enumerate(stream_file_lines(req_file)):
        line = line.strip()
        if line.startswith('CHECKS_BASE_REQ'):
            try:
                dep = line.split(' = ')[1]
                req = Requirement(dep.strip("'"))
            except (IndexError, InvalidRequirement) as e:
                errors.append(f'File `{req_file}` has an invalid base check dependency: `{line}`\n{e}')
                return

            name = req.name.lower().replace('_', '-')
            dependency = dependencies[name][req.specifier]
            dependency.append(DependencyDefinition(name, req, req_file, i, check_name))
            return

    # no `CHECKS_BASE_REQ` found in setup.py file ..
    errors.append(f'File `{req_file}` missing base check dependency `CHECKS_BASE_REQ`')


def read_check_dependencies(check=None):
    root = get_root()
    dependencies = create_dependency_data()
    errors = []

    if isinstance(check, list):
        checks = sorted(check)
    else:
        checks = sorted(get_valid_checks()) if check is None else [check]

    for check_name in checks:
        req_file = os.path.join(root, check_name, 'requirements.in')
        load_dependency_data(req_file, dependencies, errors, check_name)

    return dependencies, errors


def read_check_base_dependencies(check=None):
    root = get_root()
    dependencies = create_dependency_data()
    errors = []

    if isinstance(check, list):
        checks = sorted(check)
    else:
        checks = sorted(get_valid_checks()) if check is None else [check]

    for check_name in checks:
        if check_name.startswith('datadog_checks_'):
            continue
        req_file = os.path.join(root, check_name, 'setup.py')
        load_base_check(req_file, dependencies, errors, check_name)

    return dependencies, errors


def read_agent_dependencies():
    dependencies = create_dependency_data()
    errors = []

    load_dependency_data(get_agent_requirements(), dependencies, errors)

    return dependencies, errors
