import os
from collections import defaultdict
from copy import deepcopy

from packaging.requirements import InvalidRequirement, Requirement

from ..fs import stream_file_lines
from .constants import NOT_CHECKS, get_agent_requirements, get_root
from .utils import (
    get_project_file,
    get_valid_checks,
    has_project_file,
    load_project_file_at_cached,
    load_project_file_cached,
    write_project_file_at,
)


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


def load_dependency_data_from_metadata(check_name, dependencies, errors):
    project_data = load_project_file_cached(check_name)
    optional_dependencies = project_data['project'].get('optional-dependencies', {})

    for check_dependencies in optional_dependencies.values():
        for check_dependency in check_dependencies:
            try:
                req = Requirement(check_dependency)
            except InvalidRequirement as e:
                errors.append(
                    f'File `{check_name}/pyproject.toml` has an invalid dependency: `{check_dependency}`\n{e}'
                )
                continue

            name = req.name.lower().replace('_', '-')
            dependency = dependencies[name][req.specifier]
            dependency.append(DependencyDefinition(name, req, get_project_file(check_name), None, check_name))


def load_dependency_data_from_requirements(req_file, dependencies, errors, check_name=None):
    for i, line in enumerate(stream_file_lines(req_file)):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        try:
            req = Requirement(line)
        except InvalidRequirement as e:
            errors.append(f'File `{os.path.basename(req_file)}` has an invalid dependency: `{line}`\n{e}')
            continue

        name = req.name.lower().replace('_', '-')
        dependency = dependencies[name][req.specifier]
        dependency.append(DependencyDefinition(name, req, req_file, i, check_name))


def load_base_check(check_name, dependencies, errors):
    project_data = load_project_file_cached(check_name)
    check_dependencies = project_data['project'].get('dependencies', [])
    for check_dependency in check_dependencies:
        try:
            req = Requirement(check_dependency)
        except InvalidRequirement as e:
            errors.append(f'File `{check_name}/pyproject.toml` has an invalid dependency: `{check_dependency}`\n{e}')
            continue

        name = req.name.lower().replace('_', '-')
        if name == 'datadog-checks-base':
            dependency = dependencies[name][req.specifier]
            dependency.append(DependencyDefinition(name, req, get_project_file(check_name), None, check_name))
            break
    else:
        errors.append(f'File `{check_name}/pyproject.toml` is missing the base check dependency `datadog-checks-base`')


def load_base_check_legacy(req_file, dependencies, errors, check_name=None):
    for i, line in enumerate(stream_file_lines(req_file)):
        line = line.strip()
        if line.startswith('CHECKS_BASE_REQ'):
            try:
                dep = line.split(' = ')[1]
                req = Requirement(dep.strip("'\""))
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
        if check_name in NOT_CHECKS:
            continue

        if has_project_file(check_name):
            load_dependency_data_from_metadata(check_name, dependencies, errors)
        else:
            req_file = os.path.join(root, check_name, 'requirements.in')
            load_dependency_data_from_requirements(req_file, dependencies, errors, check_name)

    return dependencies, errors


def read_check_base_dependencies(check=None):
    root = get_root()
    dependencies = create_dependency_data()
    errors = []

    if isinstance(check, list):
        checks = sorted(check)
    else:
        checks = sorted(get_valid_checks()) if check is None else [check]

    not_required = {'datadog_checks_base', 'datadog_checks_downloader'}
    not_required.update(NOT_CHECKS)
    for check_name in checks:
        if check_name in not_required:
            continue

        if has_project_file(check_name):
            load_base_check(check_name, dependencies, errors)
        else:
            req_file = os.path.join(root, check_name, 'setup.py')
            load_base_check_legacy(req_file, dependencies, errors, check_name)

    return dependencies, errors


def update_check_dependencies_at(path, dependency_definitions):
    project_data = deepcopy(load_project_file_at_cached(path))
    optional_dependencies = project_data['project'].get('optional-dependencies', {})

    updated = False
    for dependencies in optional_dependencies.values():
        for i, old_dependency in enumerate(dependencies):
            old_requirement = Requirement(old_dependency)

            for dependency_definition in dependency_definitions:
                new_requirement = dependency_definition.requirement
                if new_requirement.name == old_requirement.name:
                    if str(new_requirement) != str(old_requirement):
                        dependencies[i] = str(new_requirement)
                        updated = True

                    break

        if updated:
            # sort, and prevent backslash escapes since strings are written using double quotes
            dependencies[:] = sorted(str(dependency).replace('"', "'") for dependency in dependencies)

    if updated:
        write_project_file_at(path, project_data)

    return updated


def update_check_dependencies(check_name, dependency_definitions):
    update_check_dependencies_at(get_project_file(check_name), dependency_definitions)


def read_agent_dependencies():
    dependencies = create_dependency_data()
    errors = []

    load_dependency_data_from_requirements(get_agent_requirements(), dependencies, errors)

    return dependencies, errors
