# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
A module with a function that substitutes parameters for
in-toto inspections. The function is expected to be called
'substitute', and takes one parameter, target_relpath, that specifies
the relative target path of the given Python package. The function is
expected to return a dictionary which maps parameter names to
parameter values, so that in-toto can substitute these parameters in
order to perform a successful inspection.
The module is expected to live here.
"""
import os.path

from packaging.utils import canonicalize_name

from .exceptions import NonDatadogPackage

EXCEPTIONS = {'datadog_checks_base', 'datadog_checks_dev', 'datadog_checks_downloader'}


def substitute(target_relpath):
    filename = os.path.basename(target_relpath)
    name, ext = os.path.splitext(filename)
    wheel_distribution_name, package_version, python_tag, _, _ = name.split('-')

    if not wheel_distribution_name.startswith('datadog_'):
        raise NonDatadogPackage(wheel_distribution_name)

    standard_distribution_name = canonicalize_name(wheel_distribution_name)

    # These names are the exceptions. In this case, the wheel distribution name
    # matches exactly the directory name of the check on GitHub.
    if wheel_distribution_name in EXCEPTIONS:
        package_github_dir = wheel_distribution_name
    # FIXME: This is the only other package at the time of writing (Sep 7 2018)
    # that does not replace `-` with `_`.
    elif wheel_distribution_name == 'datadog_go_metro':
        package_github_dir = 'go-metro'
    # Otherwise, the prefix of the wheel distribution name is expected to be
    # "datadog-", and the directory name of the check on GitHub is expected not
    # have this prefix.
    else:
        package_github_dir = wheel_distribution_name[8:]

    return {
        'package_version': package_version,
        'package_github_dir': package_github_dir,
        'python_tag': python_tag,
        'standard_distribution_name': standard_distribution_name,
        'wheel_distribution_name': wheel_distribution_name,
    }
