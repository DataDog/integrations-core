import os
from collections import defaultdict
from copy import deepcopy

from packaging.requirements import InvalidRequirement, Requirement

from ..fs import stream_file_lines, write_file_lines
from .constants import NOT_CHECKS, get_agent_requirements, get_root
from .utils import (
    get_normalized_dependency,
    get_project_file,
    get_valid_checks,
    has_project_file,
    load_project_file_at_cached,
    load_project_file_cached,
    normalize_project_name,
    write_project_file_at,
)


def create_dependency_data():
    # Structure:
    # dependency name ->
    #   Python major version ->
    #     dependency definition -> set of checks with definition
    return defaultdict(lambda: {'py2': defaultdict(set), 'py3': defaultdict(set)})


def get_dependency_set(python_versions):
    return {
        dependency_definition
        for dependency_definitions in python_versions.values()
        for dependency_definition in dependency_definitions
    }


def set_project_dependency(project, dependency, check_name):
    if 'python_version <' in dependency:
        project['py2'][dependency].add(check_name)
    elif 'python_version >' in dependency:
        project['py3'][dependency].add(check_name)
    else:
        project['py2'][dependency].add(check_name)
        project['py3'][dependency].add(check_name)


def update_project_dependency(project, dependency):
    if 'python_version <' in dependency:
        project['py2'][dependency] = project['py2'].popitem()[1]
        return project['py2'][dependency]
    elif 'python_version >' in dependency:
        project['py3'][dependency] = project['py3'].popitem()[1]
        return project['py3'][dependency]
    else:
        project['py2'][dependency] = project['py2'].popitem()[1]
        project['py3'][dependency] = project['py3'].popitem()[1]
        return project['py2'][dependency] | project['py3'][dependency]


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

            project = dependencies[normalize_project_name(req.name)]
            dependency = get_normalized_dependency(req)
            set_project_dependency(project, dependency, check_name)


def load_dependency_data_from_requirements(req_file, dependencies, errors, check_name=None):
    for line in stream_file_lines(req_file):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        try:
            req = Requirement(line)
        except InvalidRequirement as e:
            errors.append(f'File `{os.path.basename(req_file)}` has an invalid dependency: `{line}`\n{e}')
            continue

        project = dependencies[normalize_project_name(req.name)]
        dependency = get_normalized_dependency(req)
        set_project_dependency(project, dependency, check_name)


def load_base_check(check_name, dependencies, errors):
    project_data = load_project_file_cached(check_name)
    check_dependencies = project_data['project'].get('dependencies', [])
    for check_dependency in check_dependencies:
        try:
            req = Requirement(check_dependency)
        except InvalidRequirement as e:
            errors.append(f'File `{check_name}/pyproject.toml` has an invalid dependency: `{check_dependency}`\n{e}')
            continue

        name = normalize_project_name(req.name)
        if name == 'datadog-checks-base':
            dependencies[check_name] = get_normalized_dependency(req)
            break
    else:
        errors.append(f'File `{check_name}/pyproject.toml` is missing the base check dependency `datadog-checks-base`')


def load_base_check_legacy(req_file, dependencies, errors, check_name=None):
    for line in stream_file_lines(req_file):
        line = line.strip()
        if line.startswith('CHECKS_BASE_REQ'):
            try:
                dep = line.split(' = ')[1]
                req = Requirement(dep.strip("'\""))
            except (IndexError, InvalidRequirement) as e:
                errors.append(f'File `{req_file}` has an invalid base check dependency: `{line}`\n{e}')
                return

            dependencies[check_name] = get_normalized_dependency(req)
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
    dependencies = {}
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


def update_check_dependencies_at(path, dependencies):
    project_data = deepcopy(load_project_file_at_cached(path))
    optional_dependencies = project_data['project'].get('optional-dependencies', {})

    updated = False
    for old_dependencies in optional_dependencies.values():
        new_dependencies = defaultdict(set)

        for old_dependency in old_dependencies:
            old_requirement = Requirement(old_dependency)
            name = normalize_project_name(old_requirement.name)
            if name not in dependencies:
                new_dependencies[name].add(old_dependency)
                continue

            for dependency_set in dependencies[name].values():
                for dep in dependency_set:
                    new_dependencies[name].add(dep)

        new_dependencies = sorted(d for dep_set in new_dependencies.values() for d in dep_set)
        if new_dependencies != old_dependencies:
            updated = True
            old_dependencies[:] = new_dependencies

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


def update_agent_dependencies(dependencies):
    lines = sorted(
        f'{dependency_definition}\n'
        for python_versions in dependencies.values()
        for dependency_definition in get_dependency_set(python_versions)
    )

    write_file_lines(get_agent_requirements(), lines)
