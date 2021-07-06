# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from collections import defaultdict

import click
import orjson
import requests
from aiohttp import request
from aiomultiprocess import Pool
from packaging.requirements import Requirement

from ....fs import file_exists, read_file_lines, write_file_lines
from ...constants import get_agent_requirements, get_license_attribution_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

EXPLICIT_LICENSES = {
    # https://github.com/baztian/jaydebeapi/blob/master/COPYING
    'JayDeBeApi': ['LGPL-3.0-only'],
    # https://github.com/mhammond/pywin32/blob/master/adodbapi/license.txt
    'adodbapi': ['LGPL-2.1-only'],
    # https://github.com/rthalley/dnspython/blob/master/LICENSE
    'dnspython': ['ISC'],
    # https://github.com/cannatag/ldap3/blob/dev/COPYING.txt
    'ldap3': ['LGPL-3.0-only'],
    # https://github.com/paramiko/paramiko/blob/master/LICENSE
    'paramiko': ['LGPL-2.1-only'],
    # https://github.com/psycopg/psycopg2/blob/master/LICENSE
    # https://github.com/psycopg/psycopg2/blob/master/doc/COPYING.LESSER
    'psycopg2-binary': ['LGPL-3.0-only', 'BSD-3-Clause'],
    # https://github.com/Legrandin/pycryptodome/blob/master/LICENSE.rst
    'pycryptodomex': ['Unlicense', 'BSD-2-Clause'],
    # https://github.com/requests/requests-kerberos/pull/123
    'requests-kerberos': ['ISC'],
    # https://github.com/requests/requests-ntlm/blob/master/LICENSE
    'requests_ntlm': ['ISC'],
    # https://github.com/rethinkdb/rethinkdb-python/blob/master/LICENSE
    'rethinkdb': ['Apache-2.0'],
    # https://github.com/Supervisor/supervisor/blob/master/LICENSES.txt
    'supervisor': ['BSD-3-Clause-Modification'],
    # https://github.com/Cairnarvon/uptime/blob/master/COPYING.txt
    'uptime': ['BSD-2-Clause'],
    # https://github.com/hickeroar/win_inet_pton/blob/master/LICENSE
    'win-inet-pton': ['Unlicense'],
}
IGNORED_LICENSES = {'dual license'}
KNOWN_LICENSES = {
    'apache': 'Apache-2.0',
    'apache-2': 'Apache-2.0',
    'apache 2.0': 'Apache-2.0',
    'apache license 2.0': 'Apache-2.0',
    'apache license version 2.0': 'Apache-2.0',
    'apache license, version 2.0': 'Apache-2.0',
    'apache software license': 'Apache-2.0',
    'apache software license 2.0': 'Apache-2.0',
    'bsd': 'BSD-3-Clause',
    'bsd license': 'BSD-3-Clause',
    '3-clause bsd license': 'BSD-3-Clause',
    'new bsd license': 'BSD-3-Clause',
    'mit license': 'MIT',
    'psf': 'PSF',
    'psf license': 'PSF',
    'python software foundation license': 'PSF',
}
KNOWN_CLASSIFIERS = {'Python Software Foundation License': 'PSF'}
CLASSIFIER_TO_HIGHEST_SPDX = {
    'Academic Free License (AFL)': 'AFL-3.0',
    'Aladdin Free Public License (AFPL)': 'AFPL',
    'Apache Software License': 'Apache-2.0',
    'Apple Public Source License': 'APSL-2.0',
    'Artistic License': 'Artistic-2.0',
    'Attribution Assurance License': 'AAL',
    'BSD License': 'BSD-3-Clause',
    'Boost Software License 1.0 (BSL-1.0)': 'BSL-1.0',
    'CC0 1.0 Universal (CC0 1.0) Public Domain Dedication': 'CC0-1.0',
    'CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)': 'CECILL-2.1',
    'CeCILL-B Free Software License Agreement (CECILL-B)': 'CECILL-B',
    'CeCILL-C Free Software License Agreement (CECILL-C)': 'CECILL-C',
    'Common Development and Distribution License 1.0 (CDDL-1.0)': 'CDDL-1.0',
    'Common Public License': 'CPL-1.0',
    'Eclipse Public License 1.0 (EPL-1.0)': 'EPL-1.0',
    'Eiffel Forum License': 'EFL-2.0',
    'European Union Public Licence 1.1 (EUPL 1.1)': 'EUPL-1.1',
    'European Union Public Licence 1.2 (EUPL 1.2)': 'EUPL-1.2',
    'GNU Affero General Public License v3': 'AGPL-3.0-only',
    'GNU Affero General Public License v3 or later (AGPLv3+)': 'AGPL-3.0-or-later',
    'GNU General Public License v2 (GPLv2)': 'GPL-2.0-only',
    'GNU General Public License v2 or later (GPLv2+)': 'GPL-2.0-or-later',
    'GNU General Public License v3 (GPLv3)': 'GPL-3.0-only',
    'GNU General Public License v3 or later (GPLv3+)': 'GPL-3.0-or-later',
    'GNU Lesser General Public License v2 (LGPLv2)': 'LGPL-2.0-only',
    'GNU Lesser General Public License v2 or later (LGPLv2+)': 'LGPL-2.0-or-later',
    'GNU Lesser General Public License v3 (LGPLv3)': 'LGPL-3.0-only',
    'GNU Lesser General Public License v3 or later (LGPLv3+)': 'LGPL-3.0-or-later',
    'MIT License': 'MIT',
    'Mozilla Public License 1.0 (MPL)': 'MPL-1.0',
    'Mozilla Public License 1.1 (MPL 1.1)': 'MPL-1.1',
    'Mozilla Public License 2.0 (MPL 2.0)': 'MPL-2.0',
    'Netscape Public License (NPL)': 'NPL-1.1',
    'W3C License': 'W3C',
    'Zope Public License': 'ZPL-2.1',
}


def format_attribution_line(package_name, license_id, package_copyright):
    package_copyright = ' | '.join(sorted(package_copyright))
    if ',' in package_copyright:
        package_copyright = f'"{package_copyright}"'

    return f'{package_name},PyPI,{license_id},{package_copyright}\n'


def extract_license_classifier(classifier):
    return classifier.split(' :: ')[-1]


def get_known_spdx_licenses():
    url = 'https://raw.githubusercontent.com/spdx/license-list-data/v3.13/json/licenses.json'
    with requests.get(url) as response:
        license_list = orjson.loads(response.content)['licenses']

    return {data['licenseId'] for data in license_list}


async def get_data(url):
    async with request('GET', url) as response:
        try:
            info = orjson.loads(await response.read())['info']
        except Exception as e:
            raise type(e)(f'Error processing URL {url}: {e}')
        else:
            return (
                info['name'],
                info['author'] or info['maintainer'] or info['author_email'] or info['maintainer_email'] or '',
                info['license'],
                {extract_license_classifier(c) for c in info['classifiers'] if c.startswith('License ::')},
            )


async def scrape_license_data(urls):
    package_data = defaultdict(lambda: {'copyright': set(), 'licenses': [], 'classifiers': set()})

    async with Pool() as pool:
        async for package_name, package_copyright, package_license, license_classifiers in pool.map(get_data, urls):
            data = package_data[package_name]
            if package_copyright:
                data['copyright'].add(package_copyright)

            data['classifiers'].update(license_classifiers)
            if package_license:
                if ' :: ' in package_license:
                    data['classifiers'].add(extract_license_classifier(package_license))
                else:
                    data['licenses'].append(package_license)

    return package_data


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate third-party license list')
@click.option('--sync', '-s', is_flag=True, help='Generate the `LICENSE-3rdparty.csv` file')
@click.pass_context
def licenses(ctx, sync):
    """Validate third-party license list."""
    if ctx.obj['repo_choice'] != 'core':
        return

    agent_requirements_file = get_agent_requirements()
    if not file_exists(agent_requirements_file):
        abort('Out of sync, run again with the --sync flag')

    packages = defaultdict(set)
    for line in read_file_lines(agent_requirements_file):
        requirement = Requirement(line.strip())
        packages[requirement.name].add(str(requirement.specifier)[2:])

    api_urls = []
    for package, versions in packages.items():
        for version in versions:
            api_urls.append(f'https://pypi.org/pypi/{package}/{version}/json')

    package_data = asyncio.run(scrape_license_data(api_urls))
    known_spdx_licenses = {license_id.lower(): license_id for license_id in get_known_spdx_licenses()}

    package_license_errors = defaultdict(list)

    lines = ['Component,Origin,License,Copyright\n']
    for package_name, data in sorted(package_data.items()):
        if package_name in EXPLICIT_LICENSES:
            for license_id in sorted(EXPLICIT_LICENSES[package_name]):
                lines.append(format_attribution_line(package_name, license_id, data['copyright']))

            continue

        license_ids = set()
        for package_license in data['licenses']:
            package_license = package_license.strip('"')

            expanded_licenses = []
            for separator in ('/', ' OR ', ' or '):
                if separator in package_license:
                    expanded_licenses.extend(package_license.split(separator))
                    break
            else:
                expanded_licenses.append(package_license)

            for expanded_license in expanded_licenses:
                normalized_license = expanded_license.lower()
                if normalized_license in IGNORED_LICENSES:
                    continue
                elif normalized_license in KNOWN_LICENSES:
                    license_ids.add(KNOWN_LICENSES[normalized_license])
                elif normalized_license in known_spdx_licenses:
                    license_ids.add(known_spdx_licenses[normalized_license])
                else:
                    license_ids.add(expanded_license)
                    package_license_errors[package_name].append(f'unknown license: {expanded_license}')

        for classifier in data['classifiers']:
            if classifier in KNOWN_CLASSIFIERS:
                license_ids.add(KNOWN_CLASSIFIERS[classifier])
            elif classifier in CLASSIFIER_TO_HIGHEST_SPDX:
                license_ids.add(CLASSIFIER_TO_HIGHEST_SPDX[classifier])
            else:
                package_license_errors[package_name].append(f'unknown classifier: {classifier}')

        if license_ids:
            for license_id in sorted(license_ids):
                lines.append(format_attribution_line(package_name, license_id, data['copyright']))
        else:
            package_license_errors[package_name].append('no license information')

    if package_license_errors:
        for package_name, errors in package_license_errors.items():
            echo_info(package_name)
            for error in errors:
                echo_failure(error, indent=True)

        abort()

    license_attribution_file = get_license_attribution_file()
    if sync:
        write_file_lines(license_attribution_file, lines)
        echo_success('Success!')
    elif read_file_lines(license_attribution_file) != lines:
        abort('Out of sync, run again with the --sync flag')
