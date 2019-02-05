# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# 1st party.
import os.path
import re


EXCEPTIONS = {
    'datadog_checks_base',
    'datadog_checks_dev',
}


def __safe_name(name):
    '''Convert an arbitrary string to a standard distribution name
    Any runs of non-alphanumeric/. characters are replaced with a single '-'.

    https://github.com/pypa/setuptools/blob/c1243e96f05d3b13392a792144c97d9471581550/pkg_resources/__init__.py#L1317-L1322
    '''
    return re.sub('[^A-Za-z0-9.]+', '-', name)


def substitute(target_relpath):
    filename = os.path.basename(target_relpath)
    name, ext = os.path.splitext(filename)
    wheel_distribution_name, package_version, _, _, _ = name.split('-')
    assert wheel_distribution_name.startswith('datadog_'), wheel_distribution_name
    standard_distribution_name = __safe_name(wheel_distribution_name)

    # These names are the exceptions.
    if wheel_distribution_name in EXCEPTIONS:
        package_github_dir = wheel_distribution_name
    # FIXME: This is the only other package at the time of writing (Sep 7 2018)
    # that does not replace `-` with `_`.
    elif wheel_distribution_name == 'datadog_go_metro':
        package_github_dir = 'go-metro'
    else:
        package_github_dir = wheel_distribution_name[8:]

    return {
        'wheel_distribution_name': wheel_distribution_name,
        'package_version': package_version,
        'package_github_dir': package_github_dir,
        'standard_distribution_name': standard_distribution_name
    }
