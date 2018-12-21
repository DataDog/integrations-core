# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from six import iteritems

from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info
from ...constants import get_root, get_agent_requirements
from ...dep import make_catalog, read_packages


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
    failed = False
    catalog, errors = make_catalog()

    # Check unpinned
    if errors:
        for error in errors:
            echo_failure(error)
        failed = True

    # Check uniqueness
    have_multiple_versions = set()
    have_multiple_markers = set()
    for package in catalog.packages:
        versions = catalog.get_package_versions(package)
        if len(versions) > 1:
            if package.name in have_multiple_versions:
                # don't print the error multiple times
                continue

            failed = True
            have_multiple_versions.add(package.name)
            display_multiple_attributes(versions, 'Multiple versions found for package `{}`:'.format(package.name))

        markers = catalog.get_package_markers(package)
        if len(markers) > 1:
            if package.name in have_multiple_markers:
                # don't print the error multiple times
                continue

            failed = True
            have_multiple_markers.add(package.name)
            display_multiple_attributes(markers, 'Multiple markers found for package `{}`:'.format(package))

    # Check embedded env compatibility
    agent_req_file = get_agent_requirements()
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
                echo_info('    have: {}'.format(embedded_deps[package.name]))
                echo_info('    want: {}'.format(package))

    if failed:
        abort()
