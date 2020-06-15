# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# 1st party.
import argparse
import re

# 2nd party.
from .download import DEFAULT_ROOT_LAYOUT_TYPE, REPOSITORY_URL_PREFIX, ROOT_LAYOUTS, TUFDownloader
from .exceptions import NonCanonicalVersion, NonDatadogPackage

# Private module functions.


def __is_canonical(version):
    '''
    https://www.python.org/dev/peps/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
    '''

    P = r'^([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*((a|b|rc)(0|[1-9]\d*))?(\.post(0|[1-9]\d*))?(\.dev(0|[1-9]\d*))?$'
    return re.match(P, version) is not None


# Public module functions.


def download():
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
        '-v', '--verbose', action='count', default=0, help='Show verbose information about TUF and in-toto.'
    )

    args = parser.parse_args()
    repository_url_prefix = args.repository
    standard_distribution_name = args.standard_distribution_name
    version = args.version
    root_layout_type = args.type
    verbose = args.verbose

    if not standard_distribution_name.startswith('datadog-'):
        raise NonDatadogPackage(standard_distribution_name)

    if version and not __is_canonical(version):
        raise NonCanonicalVersion(version)

    tuf_downloader = TUFDownloader(
        repository_url_prefix=repository_url_prefix, root_layout_type=root_layout_type, verbose=verbose
    )
    wheel_relpath = tuf_downloader.get_wheel_relpath(standard_distribution_name, version=version)
    wheel_abspath = tuf_downloader.download(wheel_relpath)
    print(wheel_abspath)  # pylint: disable=print-statement
