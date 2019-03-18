# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# 1st party.
import argparse
import re

# 2nd party.
from .download import TUFDownloader
from .exceptions import (
    NonCanonicalVersion,
    NonDatadogPackage,
)

# 3rd party.
from tuf.exceptions import UnknownTargetError


# Private module functions.


def __is_canonical(version):
    '''
    https://www.python.org/dev/peps/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
    '''

    P = r'^([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*((a|b|rc)(0|[1-9]\d*))?(\.post(0|[1-9]\d*))?(\.dev(0|[1-9]\d*))?$'
    return re.match(P, version) is not None


def __get_wheel_distribution_name(standard_distribution_name):
    # https://www.python.org/dev/peps/pep-0491/#escaping-and-unicode
    return re.sub('[^\\w\\d.]+', '_', standard_distribution_name, re.UNICODE)


# Public module functions.


def download():
    parser = argparse.ArgumentParser()

    parser.add_argument('standard_distribution_name', type=str,
                        help='Standard distribution name of the desired Datadog check.')

    parser.add_argument('--version', type=str, default=None,
                        help='The version number of the desired Datadog check.')

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Show verbose information about TUF and in-toto.')

    args = parser.parse_args()
    standard_distribution_name = args.standard_distribution_name
    version = args.version
    verbose = args.verbose

    if not standard_distribution_name.startswith('datadog-'):
        raise NonDatadogPackage(standard_distribution_name)
    else:
        wheel_distribution_name = __get_wheel_distribution_name(standard_distribution_name)
        tuf_downloader = TUFDownloader(verbose=verbose)

        if not version:
            version = tuf_downloader.get_latest_version(standard_distribution_name, wheel_distribution_name)
        else:
            if not __is_canonical(version):
                raise NonCanonicalVersion(version)

        target_relpath = 'simple/{}/{}-{}-py2.py3-none-any.whl'\
                         .format(standard_distribution_name,
                                 wheel_distribution_name, version)

        try:
            target_abspath = tuf_downloader.download(target_relpath)
        except UnknownTargetError:
            raise NoSuchDatadogPackageOrVersion(standard_distribution_name, version)

        print(target_abspath)  # pylint: disable=print-statement
