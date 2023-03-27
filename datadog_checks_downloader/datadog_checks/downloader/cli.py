# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# 1st party.
import argparse
import os
import re
import sys

# 2nd party.
from .download import DEFAULT_ROOT_LAYOUT_TYPE, REPOSITORY_URL_PREFIX, ROOT_LAYOUTS, TUFDownloader
from .exceptions import NonCanonicalVersion, NonDatadogPackage

# Private module functions.


def __is_canonical(version):
    """
    https://www.python.org/dev/peps/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
    """

    P = r'^([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*((a|b|rc)(0|[1-9]\d*))?(\.post(0|[1-9]\d*))?(\.dev(0|[1-9]\d*))?$'
    return re.match(P, version) is not None


def __find_shipped_integrations():
    # Recurse up from site-packages until we find the Agent root directory.
    # The relative path differs between operating systems.
    root = os.path.dirname(os.path.abspath(__file__))
    filename = 'requirements-agent-release.txt'

    integrations = set()

    while True:
        file_path = os.path.join(root, filename)
        if os.path.isfile(file_path):
            break

        new_root = os.path.dirname(root)
        if new_root == root:
            return integrations

        root = new_root

    with open(file_path, 'rb') as f:
        contents = f.read().decode('utf-8')

    for line in contents.splitlines():
        integration, separator, _ = line.strip().partition('==')
        if separator:
            integrations.add(integration)

    return integrations


def instantiate_downloader():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'standard_distribution_name', type=str, help='Standard distribution name of the desired Datadog check.'
    )

    parser.add_argument(
        '--repository', type=str, default=REPOSITORY_URL_PREFIX, help='The complete URL prefix for the TUF repository.'
    )

    parser.add_argument('--version', type=str, default=None, help='The version number of the desired Datadog check.')

    parser.add_argument(
        '--type',
        type=str,
        default=DEFAULT_ROOT_LAYOUT_TYPE,
        choices=list(ROOT_LAYOUTS),
        help='The type of integration.',
    )

    parser.add_argument(
        '--force', action='store_true', help='Force download even if the type of integration may be incorrect.'
    )

    parser.add_argument(
        '--unsafe-disable-verification',
        action='store_true',
        help=(
            'Disable TUF and in-toto integrity verification. '
            'To use only if TUF or in-toto verification fails due to a bug and not an attack.'
        ),
    )

    parser.add_argument('--ignore-python-version', action='store_true', help='Ignore Python version requirements.')

    parser.add_argument(
        '-v', '--verbose', action='count', default=0, help='Show verbose information about TUF and in-toto.'
    )

    args = parser.parse_args()
    repository_url_prefix = args.repository
    standard_distribution_name = args.standard_distribution_name
    version = args.version
    root_layout_type = args.type
    force = args.force
    ignore_python_version = args.ignore_python_version
    verbose = args.verbose

    if not standard_distribution_name.startswith('datadog-'):
        raise NonDatadogPackage(standard_distribution_name)

    if version and not __is_canonical(version):
        raise NonCanonicalVersion(version)

    if root_layout_type != 'core':
        shipped_integrations = __find_shipped_integrations()
        if standard_distribution_name in shipped_integrations:
            sys.stderr.write(
                '{}: {} is a known core integration'.format('WARNING' if force else 'ERROR', standard_distribution_name)
            )
            sys.stderr.flush()

            if not force:
                sys.exit(1)

    tuf_downloader = TUFDownloader(
        repository_url_prefix=repository_url_prefix,
        root_layout_type=root_layout_type,
        verbose=verbose,
        disable_verification=args.unsafe_disable_verification,
    )

    return tuf_downloader, standard_distribution_name, version, ignore_python_version


def run_downloader(tuf_downloader, standard_distribution_name, version, ignore_python_version):
    wheel_relpath = tuf_downloader.get_wheel_relpath(
        standard_distribution_name, version=version, ignore_python_version=ignore_python_version
    )
    wheel_abspath = tuf_downloader.download(wheel_relpath)
    print(wheel_abspath)  # pylint: disable=print-statement


# Public module functions.


def download():
    tuf_downloader, standard_distribution_name, version, ignore_python_version = instantiate_downloader()
    run_downloader(tuf_downloader, standard_distribution_name, version, ignore_python_version)
