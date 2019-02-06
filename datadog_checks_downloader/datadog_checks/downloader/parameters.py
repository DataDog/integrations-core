# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# 1st party.
import os.path

# 3rd party.
# NOTE: We assume that setuptools is installed by default.
from pkg_resources import safe_name


EXCEPTIONS = {
    'datadog_checks_base',
    'datadog_checks_dev',
}


def substitute(target_relpath):
    filename = os.path.basename(target_relpath)
    name, ext = os.path.splitext(filename)
    wheel_distribution_name, package_version, _, _, _ = name.split('-')
    assert wheel_distribution_name.startswith('datadog_'), wheel_distribution_name
    standard_distribution_name = safe_name(wheel_distribution_name)

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
