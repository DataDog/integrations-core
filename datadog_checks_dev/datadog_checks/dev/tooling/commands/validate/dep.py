# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from six import iteritems

from ..utils import CONTEXT_SETTINGS, abort, echo_failure, echo_info
from ...constants import get_root, AGENT_REQUIREMENTS
from ...dep import collect_packages, read_packages
from ....utils import get_next


def display_multiple_attributes(attributes, message):
    echo_failure(message)
    for attribute, checks in sorted(iteritems(attributes)):
        if len(checks) == 1:
            echo_info('    {}: {}'.format(attribute, checks[0]))
        elif len(checks) == 2:
            echo_info('    {}: {} and {}'.format(attribute, checks[0], checks[1]))
        else:
            remaining = len(checks) - 2
            echo_info('    {}: {}, {}, and {} other{}'.format(
                attribute,
                checks[0],
                checks[1],
                remaining,
                's' if remaining > 1 else ''
            ))


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Verify dependencies across all checks'
)
def dep():
    """
    This command will:

    * Verify the uniqueness of dependency versions across all checks.
    * Verify all the dependencies are pinned.
    * Verify the embedded Python environment defined in the base check and requirements
      listed in every integration are compatible.
    """
    catalog = collect_packages()
    failed = False

    # Check uniqueness and unpinned
    for package in catalog.packages:
        versions = catalog.get_package_versions(package)
        if len(versions) > 1:
            failed = True
            display_multiple_attributes(versions, 'Multiple versions found for package `{}`:'.format(package))
        else:
            version, checks = get_next(iteritems(versions))
            if version is None:
                failed = True
                echo_failure('Unpinned dependency `{}` in the `{}` check.'.format(package, checks[0]))

        markers = catalog.get_package_markers(package)
        if len(markers) > 1:
            failed = True
            display_multiple_attributes(markers, 'Multiple markers found for package `{}`:'.format(package))

    # Check embedded env compatibility
    agent_req_file = os.path.join(get_root(), AGENT_REQUIREMENTS)
    embedded_deps = {p.name: p for p in read_packages(agent_req_file)}
    for check_name in sorted(os.listdir(get_root())):
        for package in catalog.get_check_packages(check_name):
            if package.name not in embedded_deps:
                failed = True
                echo_failure('Dependency `{}` for check `{}` missing from the embedded environment'.format(
                    package.name, check_name
                ))
            elif embedded_deps[package.name] != package:
                failed = True
                echo_failure('Dependency `{}` mismatch for check `{}` in the embedded environment'.format(
                    package.name, check_name
                ))
                echo_failure('    have: {}'.format(embedded_deps[package.name]))
                echo_failure('    want: {}'.format(package))

    if failed:
        abort()
