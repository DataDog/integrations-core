import os
from collections import defaultdict

from packaging.requirements import InvalidRequirement, Requirement

from ..utils import stream_file_lines
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

        name = req.name.lower()
        dependency = dependencies[name][req.specifier]
        dependency.append(DependencyDefinition(name, req, req_file, i, check_name))


def read_check_dependencies():
    root = get_root()
    dependencies = create_dependency_data()
    errors = []

    for check_name in get_valid_checks():
        req_file = os.path.join(root, check_name, 'requirements.in')
        load_dependency_data(req_file, dependencies, errors, check_name)

    return dependencies, errors


def read_agent_dependencies():
    dependencies = create_dependency_data()
    errors = []

    load_dependency_data(get_agent_requirements(), dependencies, errors)

    return dependencies, errors
