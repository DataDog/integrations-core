#!/usr/bin/env python

# 1st party.
import re

# 2nd party.
from .download import TUFDownloader

# 3rd party.
import click

from pkg_resources import parse_version


# Exceptions


class NonDatadogPackageException(Exception):


    def __init__(self, standard_distribution_name):
        self.standard_distribution_name = standard_distribution_name


    def __str__(self):
        return '{} is not a Datadog package!'\
               .format(self.standard_distribution_name)



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
        return 'No version found for {} !'\
                .format(self.standard_distribution_name)


# Private module functions.


def __get_latest_version(tuf_downloader, standard_distribution_name,
                         wheel_distribution_name):
    target_relpath = 'simple/{}/index.html'.format(standard_distribution_name)
    # NOTE: We do not perform in-toto inspection for simple indices; only for
    # wheels.
    target_abspath = tuf_downloader.download(target_relpath,
                                             download_in_toto_metadata=False)

    pattern = "<a href='(" + wheel_distribution_name + \
              "-(.*?)-py2\.py3-none-any\.whl)'>(.*?)<\/a><br \/>"
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


def __wheel_distribution_name(standard_distribution_name):
    # https://www.python.org/dev/peps/pep-0491/#escaping-and-unicode
    return re.sub('[^\w\d.]+', '_', standard_distribution_name, re.UNICODE)



@click.command()
@click.argument('standard_distribution_name')
@click.option('--version', default=None, show_default=True,
              help='The version number for the integration')
@click.option('-v', '--verbose', count=True, default=0, show_default=True,
              help='Show verbose information about TUF and in-toto')
def download(standard_distribution_name, version, verbose):
    if not standard_distribution_name.startswith('datadog-'):
        raise NonDatadogPackageException(standard_distribution_name)
    else:
        wheel_distribution_name = \
                        __wheel_distribution_name(standard_distribution_name)
        tuf_downloader = TUFDownloader(verbose=verbose)

        if not version:
            version = __get_latest_version(tuf_downloader,
                                           standard_distribution_name,
                                           wheel_distribution_name)

        target_relpath = 'simple/{}/{}-{}-py2.py3-none-any.whl'\
                         .format(standard_distribution_name,
                                 wheel_distribution_name, version)
        target_abspath = tuf_downloader.download(target_relpath)

        click.echo(target_abspath)
