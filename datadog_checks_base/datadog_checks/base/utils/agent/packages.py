# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from importlib.metadata import distributions

DATADOG_CHECK_PREFIX = 'datadog-'


def get_datadog_wheels():
    packages = set()
    for package in distributions():
        project_name = package.metadata['Name']
        if project_name.startswith(DATADOG_CHECK_PREFIX):
            name = project_name[len(DATADOG_CHECK_PREFIX) :].replace('-', '_')
            packages.add(name)

    return sorted(packages)[::-1]
