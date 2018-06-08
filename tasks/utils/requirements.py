# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

from .common import load_manifest


# Maps the Python platform strings to the ones we have in the manifest
PLATFORMS_TO_PY = {
    'windows': 'win32',
    'mac_os': 'darwin',
    'linux': 'linux2',
}
ALL_PLATFORMS = sorted(PLATFORMS_TO_PY.keys())


def get_requirement_line(check, version):
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
        raise Exception("Can't parse the 'supported_os' list for the check {}: {}".format(check, platforms))


def update_requirements(req_file, check, newline):
    """
    Replace the requirements line for the given check
    """
    with open(req_file, 'r') as f:
        lines = f.readlines()

    with open(req_file, 'w') as f:
        for line in lines:
            check_name = line.split("==")[0]
            if check_name == check:
                f.write(newline + '\n')
            else:
                f.write(line)
