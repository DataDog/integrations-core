# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# 1st party.
import argparse
import os
import re
import sys
from pathlib import Path

# 2nd party.
from .download import DEFAULT_ROOT_LAYOUT_TYPE, REPOSITORY_URL_PREFIX, ROOT_LAYOUTS, TUFDownloader
from .download_v2 import TUFPointerDownloader
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

    parser.add_argument(
        '--format',
        type=str,
        default='v1',
        choices=['v1', 'v2'],
        help=(
            'Repository format: v1 (default, simple-index + in-toto) or '
            'v2 (pointer-file + sha256, used by agent-integrations-tuf).'
        ),
    )

    parser.add_argument(
        '--root-json',
        type=str,
        default=None,
        metavar='PATH',
        help=(
            '[v2 only] Path to the initial root.json that bootstraps the TUF trust chain. '
            'Defaults to TOFU (fetch from the repository) when omitted.'
        ),
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
    # Peek at --format before delegating.  instantiate_downloader() handles v1
    # only; we handle v2 here so that v1 call-sites are unaffected.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--format', default='v1', choices=['v1', 'v2'])
    partial_args, _ = parser.parse_known_args()

    if partial_args.format == 'v2':
        _download_v2()
    else:
        tuf_downloader, standard_distribution_name, version, ignore_python_version = instantiate_downloader()
        run_downloader(tuf_downloader, standard_distribution_name, version, ignore_python_version)


def _download_v2():
    """Entry point for the v2 pointer-file download path."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'standard_distribution_name',
        type=str,
        help='Standard distribution name of the desired Datadog check, e.g. datadog-postgres.',
    )
    parser.add_argument('--repository', type=str, required=True, help='HTTPS base URL of the v2 TUF repository.')
    parser.add_argument('--version', type=str, default=None, help='Version to download (default: latest stable).')
    parser.add_argument(
        '--root-json',
        type=str,
        default=None,
        metavar='PATH',
        help='Path to the initial root.json trust anchor (omit to use TOFU).',
    )
    parser.add_argument(
        '--unsafe-disable-verification',
        action='store_true',
        help='Disable TUF verification and wheel digest checks.',
    )
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--format', default='v2', choices=['v1', 'v2'])  # consumed upstream; kept for completeness

    # v1 flags that are not applicable in v2: accept and warn so that callers
    # upgrading from v1 get a clear message instead of an argument error.
    parser.add_argument('--type', type=str, default=None, dest='_type_ignored')
    parser.add_argument('--force', action='store_true', dest='_force_ignored')
    parser.add_argument('--ignore-python-version', action='store_true', dest='_ignore_python_version')

    args = parser.parse_args()

    if not args.standard_distribution_name.startswith('datadog-'):
        raise NonDatadogPackage(args.standard_distribution_name)

    if args.version and not re.match(
        r'^([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*((a|b|rc)(0|[1-9]\d*))?(\.post(0|[1-9]\d*))?(\.dev(0|[1-9]\d*))?$',
        args.version,
    ):
        raise NonCanonicalVersion(args.version)

    if args._type_ignored is not None:
        sys.stderr.write('WARNING: --type is not applicable with --format v2 and will be ignored.\n')
    if args._ignore_python_version:
        sys.stderr.write(
            'NOTE: --ignore-python-version is not applicable with --format v2 '
            '(wheel selection happens at publish time).\n'
        )

    trust_anchor = Path(args.root_json) if args.root_json else None
    downloader = TUFPointerDownloader(
        repository_url=args.repository,
        trust_anchor=trust_anchor,
        verbose=args.verbose,
        disable_verification=args.unsafe_disable_verification,
    )
    wheel_path = downloader.download(args.standard_distribution_name, version=args.version)
    print(wheel_path)  # pylint: disable=print-statement
