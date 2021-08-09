import glob
from os.path import join

import yaml
from genericpath import isfile
from yaml.error import YAMLError
from yaml.loader import SafeLoader

from datadog_checks.dev.tooling.commands.console import echo_failure
from datadog_checks.dev.tooling.constants import get_root


def initialize_path(directory):
    path = []
    path.append('./')

    path.append(get_default_snmp_profiles_path())

    if directory:
        path.append(directory)

    return path


def find_profile_in_path(profile_name, path, line=True):
    file_contents = None
    errors = []
    for directory_path in path:
        if isfile(join(directory_path, profile_name)):
            try:
                with open(join(directory_path, profile_name)) as f:
                    if line:
                        file_contents = yaml.load(f.read(), Loader=SafeLineLoader)
                    else:
                        file_contents = yaml.safe_load(f.read())
            except YAMLError as e:
                errors.append((e, join(directory_path, profile_name)))
        if file_contents:
            return file_contents
    for e, path in errors:
        echo_failure("Error in the YAML file " + path)
        echo_failure(e)
    return file_contents


def exist_profile_in_path(profile_name, path):
    if profile_name:
        for directory_path in path:
            if isfile(join(directory_path, profile_name)):
                return True
    return False


def get_profile(profile_name, line=True):
    file_contents = None
    if isfile(profile_name):
        try:
            with open(profile_name) as f:
                if line:
                    file_contents = yaml.load(f.read(), Loader=SafeLineLoader)
                else:
                    file_contents = yaml.safe_load(f.read())
        except YAMLError:
            file_contents = None
    return file_contents


def get_default_snmp_profiles_path():
    return join(get_root(), 'snmp', 'datadog_checks', 'snmp', 'data', 'profiles')


def get_all_profiles_directory(directory):
    return glob.glob(join(directory, "*.yaml"))


class SafeLineLoader(SafeLoader):
    def construct_mapping(self, node, deep=False):
        """
        Function to allow retrieving the line of the duplicated metric.\n
        It adds the key "__line__" with the value of the line it is to every key in the mapping created by yaml.load
        """
        mapping = super(SafeLineLoader, self).construct_mapping(node, deep=deep)
        # Add 1 so line numbering starts at 1
        mapping['__line__'] = node.start_mark.line + 1
        return mapping
