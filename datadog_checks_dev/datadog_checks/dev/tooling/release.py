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


def get_agent_requirement_line(check, version):
    """
    Compose a text line to be used in a requirements.txt file to install a check
    pinned to a specific version.
    """
    # base check and siblings have no manifest
    if check in ('datadog_checks_base', 'datadog_checks_tests_helper'):
        return '{}=={}'.format(check, version)

    m = load_manifest(check)
    platforms = sorted(m.get('supported_os', []))

    # all platforms
    if platforms == ALL_PLATFORMS:
        return '{}=={}'.format(check, version)
    # one specific platform
    elif len(platforms) == 1:
        return "{}=={}; sys_platform == '{}'".format(check, version, PLATFORMS_TO_PY.get(platforms[0]))
    # assuming linux+mac here for brevity
    elif platforms and 'windows' not in platforms:
        return "{}=={}; sys_platform != 'win32'".format(check, version)
    else:
        raise Exception("Can't parse the `supported_os` list for the check {}: {}".format(check, platforms))


def update_agent_requirements(req_file, check, newline):
    """
    Replace the requirements line for the given check
    """
    old_lines = read_file_lines(req_file)
    new_lines = []

    for line in old_lines:
        check_name = line.split('==')[0]
        if check_name == check:
            new_lines.append('{}\n'.format(newline))
        else:
            new_lines.append(line)

    write_file_lines(req_file, new_lines)
