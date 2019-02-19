# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# 1st party.
import argparse
import re

# 2nd party.
from .download import TUFDownloader

# 3rd party.
# NOTE: We assume that setuptools is installed by default.
from pkg_resources import parse_version
from tuf.exceptions import UnknownTargetError


# Exceptions


class NonCanonicalVersionException(Exception):


    def __init__(self, version):
        self.version = version


    def __str__(self):
        return '{} is not a valid PEP 440 version!'.format(self.version)


class NonDatadogPackageException(Exception):


    def __init__(self, standard_distribution_name):
        self.standard_distribution_name = standard_distribution_name


    def __str__(self):
        return '{} is not a Datadog package!'.format(self.standard_distribution_name)


class NoSuchDatadogPackageException(Exception):


    def __init__(self, standard_distribution_name):
        self.standard_distribution_name = standard_distribution_name


    def __str__(self):
        return 'Could not find the {} package!'.format(self.standard_distribution_name)


class NoSuchDatadogPackageOrVersionException(Exception):


    def __init__(self, standard_distribution_name, version):
        self.standard_distribution_name = standard_distribution_name
        self.version = version


    def __str__(self):
        return 'Either no {} package, or {} version!'.format(self.standard_distribution_name, self.version)


class SimpleIndexException(Exception):


    def __init__(self, href, text):
        self.href = href
        self.text = text


    def __str__(self):
        return '{} != {}'.format(self.href, self.text)


class MissingVersionsException(Exception):


    def __init__(self, standard_distribution_name):
        self.standard_distribution_name = standard_distribution_name


    def __str__(self):
        return 'No version found for {} !'.format(self.standard_distribution_name)


# Private module functions.


def __get_latest_version(tuf_downloader, standard_distribution_name, wheel_distribution_name):
    target_relpath = 'simple/{}/index.html'.format(standard_distribution_name)

    try:
        # NOTE: We do not perform in-toto inspection for simple indices; only for wheels.
        target_abspath = tuf_downloader.download(target_relpath, download_in_toto_metadata=False)
    except UnknownTargetError:
        raise NoSuchDatadogPackageException(standard_distribution_name)

    pattern = "<a href='(" + wheel_distribution_name + "-(.*?)-py2\\.py3-none-any\\.whl)'>(.*?)</a><br />"
    versions = []

    with open(target_abspath) as simple_index:
        for line in simple_index:
            match = re.match(pattern, line)
            if match:
                href = match.group(1)
                version = match.group(2)
                text = match.group(3)
                if href != text:
                    raise SimpleIndexException(href, text)
                else:
                    # https://setuptools.readthedocs.io/en/latest/pkg_resources.html#parsing-utilities
                    versions.append(parse_version(version))

    if not len(versions):
        raise MissingVersionsException(standard_distribution_name)
    else:
        return max(versions)


def __is_canonical(version):
    '''
    https://www.python.org/dev/peps/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
    '''

    P = r'^([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*((a|b|rc)(0|[1-9]\d*))?(\.post(0|[1-9]\d*))?(\.dev(0|[1-9]\d*))?$'
    return re.match(P, version) is not None


def __wheel_distribution_name(standard_distribution_name):
    # https://www.python.org/dev/peps/pep-0491/#escaping-and-unicode
    return re.sub('[^\\w\\d.]+', '_', standard_distribution_name, re.UNICODE)


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
        raise NonDatadogPackageException(standard_distribution_name)
    else:
        wheel_distribution_name = __wheel_distribution_name(standard_distribution_name)
        tuf_downloader = TUFDownloader(verbose=verbose)

        if not version:
            version = __get_latest_version(tuf_downloader, standard_distribution_name, wheel_distribution_name)
        else:
            if not __is_canonical(version):
                raise NonCanonicalVersionException(version)

        target_relpath = 'simple/{}/{}-{}-py2.py3-none-any.whl'\
                         .format(standard_distribution_name,
                                 wheel_distribution_name, version)

        try:
            target_abspath = tuf_downloader.download(target_relpath)
        except UnknownTargetError:
            raise NoSuchDatadogPackageOrVersionException(standard_distribution_name, version)

        print(target_abspath)
