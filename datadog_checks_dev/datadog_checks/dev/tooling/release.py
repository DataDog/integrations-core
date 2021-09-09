# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import sys

from ..errors import ManifestError
from ..fs import chdir, read_file, read_file_lines, write_file, write_file_lines
from ..subprocess import run_command
from .utils import get_version_file, load_manifest

# Maps the Python platform strings to the ones we have in the manifest
PLATFORMS_TO_PY = {'windows': 'win32', 'mac_os': 'darwin', 'linux': 'linux2'}
ALL_PLATFORMS = sorted(PLATFORMS_TO_PY)
VERSION = re.compile(r'__version__ *= *(?:[\'"])(.+?)(?:[\'"])')
DATADOG_PACKAGE_PREFIX = 'datadog-'


def get_release_tag_string(check_name, version_string):
    """
    Compose a string to use for release tags
    """
    if check_name:
        return f'{check_name}-{version_string}'
    else:
        return version_string


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
    elif folder_name == 'datadog_checks_downloader':
        return 'datadog-checks-downloader'
    elif folder_name == 'datadog_checks_dependency_provider':
        return 'datadog-checks-dependency-provider'

    return f"{DATADOG_PACKAGE_PREFIX}{folder_name.replace('_', '-')}"


def get_folder_name(package_name):
    """
    Given a Python package name for a check, return the corresponding folder
    name in the git repo
    """
    if package_name == 'datadog-checks-base':
        return 'datadog_checks_base'
    elif package_name == 'datadog-checks-downloader':
        return 'datadog_checks_downloader'
    elif package_name == 'datadog-checks-dependency-provider':
        return 'datadog_checks_dependency_provider'

    return package_name.replace('-', '_')[len(DATADOG_PACKAGE_PREFIX) :]


def get_agent_requirement_line(check, version):
    """
    Compose a text line to be used in a requirements.txt file to install a check
    pinned to a specific version.
    """
    package_name = get_package_name(check)

    # no manifest
    if check in ('datadog_checks_base', 'datadog_checks_downloader', 'datadog_checks_dependency_provider'):
        return f'{package_name}=={version}'

    m = load_manifest(check)
    platforms = sorted(m.get('supported_os', []))

    # all platforms
    if platforms == ALL_PLATFORMS:
        return f'{package_name}=={version}'
    # one specific platform
    elif len(platforms) == 1:
        return f"{package_name}=={version}; sys_platform == '{PLATFORMS_TO_PY.get(platforms[0])}'"
    elif platforms:
        if 'windows' not in platforms:
            return f"{package_name}=={version}; sys_platform != 'win32'"
        elif 'mac_os' not in platforms:
            return f"{package_name}=={version}; sys_platform != 'darwin'"
        elif 'linux' not in platforms:
            return f"{package_name}=={version}; sys_platform != 'linux2'"

    raise ManifestError(f"Can't parse the `supported_os` list for the check {check}: {platforms}")


def update_agent_requirements(req_file, check, newline):
    """
    Replace the requirements line for the given check
    """
    package_name = get_package_name(check)
    lines = read_file_lines(req_file)

    for i, line in enumerate(lines):
        current_package_name = line.split('==')[0]

        if current_package_name == package_name:
            lines[i] = f'{newline}\n'
            break

    write_file_lines(req_file, sorted(lines))


def build_package(package_path, sdist):
    with chdir(package_path):
        # Clean up: Files built previously and now deleted might still persist in build directory
        # and will be included in the final wheel. Cleaning up before avoids that.
        result = run_command([sys.executable, 'setup.py', 'clean', '--all'], capture='out')
        if result.code != 0:
            return result

        result = run_command([sys.executable, 'setup.py', 'bdist_wheel', '--universal'], capture='out')
        if result.code != 0:
            return result

        if sdist:
            result = run_command([sys.executable, 'setup.py', 'sdist'], capture='out')
            if result.code != 0:
                return result

    return result
