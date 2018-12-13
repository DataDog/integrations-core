# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from six import iteritems

from ..utils import CONTEXT_SETTINGS, abort, echo_failure, echo_info
from ...dep import collect_packages
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
    short_help='Verify the uniqueness of dependency versions'
)
def dep():
    """Verify the uniqueness of dependency versions across all checks."""
    all_packages, _ = collect_packages()
    failed = False

    for package, package_data in sorted(iteritems(all_packages)):
        versions = package_data['versions']
        if len(versions) > 1:
            failed = True
            display_multiple_attributes(versions, 'Multiple versions found for package `{}`:'.format(package))
        else:
            version, checks = get_next(iteritems(versions))
            if version is None:
                failed = True
                echo_failure('Unpinned dependency `{}` in the `{}` check.'.format(package, checks[0]))

        markers = package_data['markers']
        if len(markers) > 1:
            failed = True
            display_multiple_attributes(markers, 'Multiple markers found for package `{}`:'.format(package))

    if failed:
        abort()
