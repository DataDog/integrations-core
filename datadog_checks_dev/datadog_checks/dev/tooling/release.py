# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from .utils import get_version_file, load_manifest
from ..utils import read_file, read_file_lines, write_file, write_file_lines

# Maps the Python platform strings to the ones we have in the manifest
PLATFORMS_TO_PY = {
    'windows': 'win32',
    'mac_os': 'darwin',
    'linux': 'linux2',
}
ALL_PLATFORMS = sorted(PLATFORMS_TO_PY)
VERSION = re.compile(r'__version__ *= *(?:[\'"])(.+?)(?:[\'"])')
DATADOG_PACKAGE_PREFIX = 'datadog-'


def get_release_tag_string(check_name, version_string):
    """
    Compose a string to use for release tags
    """
    return '{}-{}'.format(check_name, version_string)


def update_version_module(check_name, old_ver, new_ver):
    """
    Change the Python code in the __about__.py module so that `__version__`
    contains the new value.
    """
    version_file = get_version_file(check_name)
    contents = read_file(version_file)

    contents = contents.replace(old_ver, new_ver)
    write_file(version_file, contents)


def get_package_name(folder_name):
    """
    Given a folder name for a check, return the name of the
    corresponding Python package
    """
    if folder_name == 'datadog_checks_base':
        return 'datadog-checks-base'

    return '{}{}'.format(DATADOG_PACKAGE_PREFIX, folder_name.replace('_', '-'))


def get_folder_name(package_name):
    """
    Given a Python package name for a check, return the corresponding folder
    name in the git repo
    """
    if package_name == 'datadog-checks-base':
        return 'datadog_checks_base'

    return package_name.replace('-', '_')[len(DATADOG_PACKAGE_PREFIX):]


def get_agent_requirement_line(check, version):
    """
    Compose a text line to be used in a requirements.txt file to install a check
    pinned to a specific version.
    """
    package_name = get_package_name(check)

    # base check has no manifest
    if check == 'datadog_checks_base':
        return '{}=={}'.format(package_name, version)

    m = load_manifest(check)
    platforms = sorted(m.get('supported_os', []))

    # all platforms
    if platforms == ALL_PLATFORMS:
        return '{}=={}'.format(package_name, version)
    # one specific platform
    elif len(platforms) == 1:
        return "{}=={}; sys_platform == '{}'".format(
            package_name, version, PLATFORMS_TO_PY.get(platforms[0])
        )
    elif platforms:
        if 'windows' not in platforms:
            return "{}=={}; sys_platform != 'win32'".format(package_name, version)
        elif 'mac_os' not in platforms:
            return "{}=={}; sys_platform != 'darwin'".format(package_name, version)
        elif 'linux' not in platforms:
            return "{}=={}; sys_platform != 'linux2'".format(package_name, version)

    raise Exception("Can't parse the `supported_os` list for the check {}: {}".format(check, platforms))


def update_agent_requirements(req_file, check, newline):
    """
    Replace the requirements line for the given check
    """
    package_name = get_package_name(check)
    lines = read_file_lines(req_file)

    for i, line in enumerate(lines):
        current_package_name = line.split('==')[0]

        if current_package_name == package_name:
            lines[i] = '{}\n'.format(newline)
            break

    write_file_lines(req_file, sorted(lines))
