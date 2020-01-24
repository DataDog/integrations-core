# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pkg_resources

DATADOG_CHECK_PREFIX = "datadog-"


def get_datadog_wheels():
    packages = []
    dist = list(pkg_resources.working_set)
    for package in dist:
        if package.project_name.startswith(DATADOG_CHECK_PREFIX):
            name = package.project_name[len(DATADOG_CHECK_PREFIX) :].replace('-', '_')
            packages.append(name)

    return sorted(packages)[::-1]
