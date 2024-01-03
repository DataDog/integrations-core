# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import concurrent.futures
import difflib
import io
import os
import re
import tarfile
from collections import defaultdict
from contextlib import closing
from zipfile import ZipFile

import click
import orjson
import requests
from packaging.requirements import Requirement

from ....fs import file_exists, read_file_lines, write_file_lines
from ...constants import (
    get_agent_requirements,
    get_copyright_ignore_re,
    get_copyright_locations_re,
    get_copyright_re,
    get_license_attribution_file,
)
from ...github import get_auth_info
from ...utils import get_extra_license_files, read_license_file_rows
from ..console import CONTEXT_SETTINGS, abort, annotate_error, echo_failure, echo_info, echo_success, echo_warning

EXPLICIT_LICENSES = {
    # https://github.com/aerospike/aerospike-client-python/blob/master/LICENSE
    'aerospike': ['Apache-2.0'],
    # https://github.com/baztian/jaydebeapi/blob/master/COPYING
    'JayDeBeApi': ['LGPL-3.0-only'],
    # https://github.com/pyca/cryptography/blob/main/LICENSE
    'cryptography': ['Apache-2.0', 'BSD-3-Clause', 'PSF'],
    # https://github.com/rthalley/dnspython/blob/master/LICENSE
    'dnspython': ['ISC'],
    # https://github.com/cannatag/ldap3/blob/dev/COPYING.txt
    'ldap3': ['LGPL-3.0-only'],
    # https://cloudera.github.io/cm_api/
    'cm-client': ['Apache-2.0'],
    # https://github.com/oauthlib/oauthlib/blob/master/LICENSE
    'oauthlib': ['BSD-3-Clause'],
    # https://github.com/hajimes/mmh3/blob/master/LICENSE
    'mmh3': ['CC0-1.0'],
    # https://github.com/paramiko/paramiko/blob/master/LICENSE
    'paramiko': ['LGPL-2.1-only'],
    # https://github.com/oracle/python-oracledb/blob/main/LICENSE.txt
    'oracledb': ['Apache-2.0'],
    # https://github.com/psycopg/psycopg2/blob/master/LICENSE
    # https://github.com/psycopg/psycopg2/blob/master/doc/COPYING.LESSER
    'psycopg2-binary': ['LGPL-3.0-only', 'BSD-3-Clause'],
    # https://github.com/psycopg/psycopg/blob/master/LICENSE.txt
    'psycopg': ['LGPL-3.0-only'],
    # https://github.com/psycopg/psycopg/blob/master/psycopg_pool/LICENSE.txt
    'psycopg-pool': ['LGPL-3.0-only'],
    # https://github.com/Legrandin/pycryptodome/blob/master/LICENSE.rst
    'pycryptodomex': ['Unlicense', 'BSD-2-Clause'],
    # https://github.com/requests/requests-kerberos/pull/123
    'requests-kerberos': ['ISC'],
    # https://github.com/requests/requests-ntlm/blob/master/LICENSE
    'requests-ntlm': ['ISC'],
    # https://github.com/rethinkdb/rethinkdb-python/blob/master/LICENSE
    'rethinkdb': ['Apache-2.0'],
    # https://github.com/simplejson/simplejson/blob/master/LICENSE.txt
    'simplejson': ['MIT'],
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
    'upl': 'UPL',
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
    "Universal Permissive License (UPL)": 'UPL',
    'W3C License': 'W3C',
    'Zope Public License': 'ZPL-2.1',
}

EXTRA_LICENSES = {'BSD-2-Clause'}

VALID_LICENSES = (
    EXTRA_LICENSES
    | set(KNOWN_LICENSES.values())
    | set(CLASSIFIER_TO_HIGHEST_SPDX.values())
    | set(KNOWN_CLASSIFIERS.values())
)

HEADERS = ['Component', 'Origin', 'License', 'Copyright']

ADDITIONAL_LICENSES = {
    'flup,Vendor,BSD-3-Clause,Copyright (c) 2005 Allan Saddi. All Rights Reserved.\n',
    'flup-py3,Vendor,BSD-3-Clause,"Copyright (c) 2005, 2006 Allan Saddi <allan@saddi.com> All rights reserved."\n',
}

PACKAGE_REPO_OVERRIDES = {
    'PyYAML': 'https://github.com/yaml/pyyaml',
    'contextlib2': 'https://github.com/jazzband/contextlib2',
    'dnspython': 'https://github.com/rthalley/dnspython',
    'foundationdb': 'https://github.com/apple/foundationdb',
    'in-toto': 'https://github.com/in-toto/in-toto',
    'lxml': 'https://github.com/lxml/lxml',
    'oracledb': 'https://github.com/oracle/python-oracledb',
    'packaging': 'https://github.com/pypa/packaging',
    'paramiko': 'https://github.com/paramiko/paramiko',
    'protobuf': 'https://github.com/protocolbuffers/protobuf',
    'psycopg2-binary': 'https://github.com/psycopg/psycopg2',
    'psycopg': 'https://github.com/psycopg/psycopg',
    'pycryptodomex': 'https://github.com/Legrandin/pycryptodome',
    'redis': 'https://github.com/redis/redis-py',
    'requests': 'https://github.com/psf/requests',
    'requests-toolbelt': 'https://github.com/requests/toolbelt',
    'service-identity': 'https://github.com/pyca/service-identity',
    'snowflake-connector-python': 'https://github.com/snowflakedb/snowflake-connector-python',
    'supervisor': 'https://github.com/Supervisor/supervisor',
    'tuf': 'https://github.com/theupdateframework/python-tuf',
    'typing': 'https://github.com/python/typing',
}

COPYRIGHT_ATTR_TEMPLATES = {
    'Apache-2.0': 'Copyright {year}{author}',
    'BSD-2-Clause': 'Copyright {year}{author}',
    'BSD-3-Clause': 'Copyright {year}{author}',
    'BSD-3-Clause-Modification': 'Copyright {year}{author}',
    'LGPL-2.1-only': 'Copyright (C) {year}{author}',
    'LGPL-3.0-only': 'Copyright (C) {year}{author}',
    'MIT': 'Copyright (c) {year}{author}',
    'PSF': 'Copyright (c) {year}{author}',
    'CC0-1.0': '{author}. {package_name} is dedicated to the public domain under {license}.',
    'Unlicense': '{author}. {package_name} is dedicated to the public domain under {license}.',
}


def format_attribution_line(package_name, license_id, package_copyright):
    if ',' in package_copyright:
        package_copyright = f'"{package_copyright}"'

    return f'{package_name},PyPI,{license_id},{package_copyright}\n'


def extract_classifier_value(classifier):
    return classifier.split(' :: ')[-1]


def get_known_spdx_licenses():
    url = 'https://raw.githubusercontent.com/spdx/license-list-data/v3.13/json/licenses.json'
    with requests.get(url) as response:
        license_list = orjson.loads(response.content)['licenses']

    return {data['licenseId'] for data in license_list}


def get_data(url):
    with requests.get(url) as response:
        return orjson.loads(response.content)


def scrape_license_data(urls):
    package_data = defaultdict(
        lambda: {'copyright': {}, 'licenses': set(), 'classifiers': set(), 'home_page': None, 'author': None}
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(get_data, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            resp = future.result()
            info = resp['info']
            data = package_data[(info['name'], info['version'])]
            data['urls'] = resp['urls']
            pkg_author = info['author'] or info['maintainer'] or info['author_email'] or info['maintainer_email'] or ''
            if pkg_author:
                data['author'] = pkg_author

            data['classifiers'].update(
                {extract_classifier_value(c) for c in info['classifiers'] if c.startswith('License ::')}
            )
            if package_license := info['license']:
                if ' :: ' in package_license:
                    data['classifiers'].add(extract_classifier_value(package_license))
                else:
                    data['licenses'].add(package_license)

            if home_page := info['home_page']:
                data['home_page'] = home_page

    return package_data


def collect_source_url(package_data):
    """Collect url to a tarball (preferred) or wheel (backup) for a package."""
    tarballs, wheels = [], []
    for urld in package_data['urls']:
        url = urld['url']
        if url.endswith('.tar.gz'):
            tarballs.append(url)
        elif url.endswith('.whl'):
            wheels.append(url)
        else:
            continue
    combined = tarballs + wheels
    if not combined:
        raise ValueError(
            f"No urls for packages, here are the urls for this dependency: {[u['url'] for u in package_data['urls']]}"
        )
    return combined[0]


def update_copyrights(package_name, license_id, data, ctx):
    """
    Update package data with scraped copyright attributions.
    """

    gh_repo_url = PACKAGE_REPO_OVERRIDES.get(package_name) or data['home_page']
    created_date = '' if gh_repo_url is None else probe_github(gh_repo_url, ctx)

    url = collect_source_url(data)
    cp = scrape_copyright_data(url)
    if cp:
        data['copyright'][license_id] = cp

    if data['author'] and not data['copyright'].get(license_id):
        cp = 'Copyright {}{}'.format(created_date, data['author'])
        if license_id in COPYRIGHT_ATTR_TEMPLATES:
            cp = COPYRIGHT_ATTR_TEMPLATES[license_id].format(
                year=created_date, author=data['author'], package_name=package_name, license=license_id
            )
        data['copyright'][license_id] = cp


def probe_github(url, ctx):
    """Probe GitHub API for package's repo creation date."""
    if url.endswith('/'):
        url = url[:-1]
    if 'github.com' not in url:
        return ''
    owner_repo = re.sub(r'.*github.com/', '', url)
    repo_api_url = f'https://api.github.com/repos/{owner_repo}'
    try:
        resp = requests.get(repo_api_url, auth=get_auth_info(ctx.obj))
        resp.raise_for_status()
        created_date = resp.json().get('created_at', '')
    except requests.exceptions.RequestException:
        created_date = ''
    return created_date[:4] + ' ' if created_date else created_date


def parse_license_path(tar_file_name):
    """
    Parses filepath name and returns the filepath if it is a potential copyright attribution location.
    """
    file_name_parts = tar_file_name.split("/")
    # Look at only the root-level files
    if len(file_name_parts) == 2:
        m = get_copyright_locations_re().search(file_name_parts[1])
        if m:
            return file_name_parts[1]
    return None


def generate_from_tarball(response):
    with tarfile.open(fileobj=response.raw, mode="r|gz") as archive:
        for tar_info in archive:
            if not (tar_info.islnk() or tar_info.issym()) and parse_license_path(tar_info.name):
                fh = archive.extractfile(tar_info)
                if fh is not None:
                    with closing(fh) as safe_fh:
                        yield safe_fh.read()


def generate_from_wheel(response):
    with ZipFile(io.BytesIO(response.content)) as archive:
        for name in archive.namelist():
            if parse_license_path(name):
                with archive.open(name) as fh:
                    yield fh.read()


def pick_file_generator(url):
    if url.endswith(".tar.gz"):
        return generate_from_tarball
    elif url.endswith(".whl"):
        return generate_from_wheel
    else:
        raise ValueError(f"Unknown type of archive based on this url: {url}")


def scrape_copyright_data(url_path):
    """
    Scrapes each tarfile for copyright attributions.
    """
    with requests.get(url_path, stream=True) as resp:
        for fcontents in pick_file_generator(url_path)(resp):
            if cp := find_cpy(fcontents):
                return cp
    return None


def find_cpy(data):
    """
    Performs pattern matching on input data to find copyright attributions.
    Returns the copyright attribution if found.
    """
    text = str(data, 'UTF-8')
    for line in text.splitlines():
        line = re.sub(r'.*#', '', line)
        line = line.strip()
        m = get_copyright_re().search(line)
        if not m:
            continue
        cpy = m.group(0)
        # ignore a few spurious matches from license boilerplate
        if any(ign.match(cpy) for ign in get_copyright_ignore_re()):
            continue

        cpy = cpy.strip().rstrip(',')
        if cpy:
            return cpy


def validate_extra_licenses():
    """
    Validates extra third party licenses.

    An integration may use code from an outside source or origin that is not pypi-
    it will have a file in its check directory titled `3rdparty-extra-LICENSE.csv`
    """
    lines = set()
    any_errors = False

    all_extra_licenses = get_extra_license_files()

    for license_file in all_extra_licenses:
        errors = False
        rows = read_license_file_rows(license_file)
        for line_no, row, line in rows:
            # determine if number of columns is complete by checking for None values (DictReader populates missing columns with None https://docs.python.org/3.8/library/csv.html#csv.DictReader) # noqa
            if None in row.values():
                errors = True
                any_errors = True
                echo_failure(f"{license_file}:{line_no} Has the wrong amount of columns")
                annotate_error(license_file, "Contains the wrong amount of columns", line=line_no)
                continue

            # all headers exist, no invalid headers
            all_keys = set(row)
            ALL_HEADERS = set(HEADERS)
            if all_keys != ALL_HEADERS:
                invalid_headers = all_keys.difference(ALL_HEADERS)
                if invalid_headers:
                    echo_failure(f'{license_file}:{line_no} Invalid column {invalid_headers}')
                    annotate_error(license_file, f"Detected invalid column {invalid_headers}", line=line_no)

                missing_headers = ALL_HEADERS.difference(all_keys)
                if missing_headers:
                    echo_failure(f'{license_file}:{line_no} Missing columns {missing_headers}')
                    annotate_error(license_file, f"Detected missing columns {invalid_headers}", line=line_no)

                errors = True
                any_errors = True
                continue
            license_type = row['License']
            if license_type not in VALID_LICENSES:
                errors = True
                any_errors = True
                echo_failure(f'{license_file}:{line_no} Invalid license type {license_type}')
                annotate_error(license_file, f"Detected invalid license type {license_type}", line=line_no)
                continue
            if not errors:
                lines.add(line)

    return lines, any_errors


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate third-party license list')
@click.option('--sync', '-s', is_flag=True, help='Generate the `LICENSE-3rdparty.csv` file')
@click.pass_context
def licenses(ctx, sync):
    """Validate third-party license list."""
    if ctx.obj['repo_choice'] != 'core':
        return

    agent_requirements_file = get_agent_requirements()
    if not file_exists(agent_requirements_file):
        abort("Out of sync, run 'ddev validate licenses --sync'")

    packages = defaultdict(set)
    for i, line in enumerate(read_file_lines(agent_requirements_file)):
        try:
            requirement = Requirement(line.strip())
            packages[requirement.name].add(str(requirement.specifier)[2:])
        except Exception as e:
            rel_file = os.path.basename(agent_requirements_file)
            line = i + 1
            annotate_error(agent_requirements_file, str(e).split(":")[1], line=line)
            echo_failure(f"Detected error in {rel_file}:{line} {e}")

    api_urls = []
    for package, versions in packages.items():
        for version in versions:
            api_urls.append(f'https://pypi.org/pypi/{package}/{version}/json')

    package_data = scrape_license_data(api_urls)
    known_spdx_licenses = {license_id.lower(): license_id for license_id in get_known_spdx_licenses()}

    package_license_errors = defaultdict(list)

    lines = set()
    for (package_name, _version), data in sorted(package_data.items()):
        if package_name in EXPLICIT_LICENSES:
            for license_id in sorted(EXPLICIT_LICENSES[package_name]):
                data['licenses'].add(license_id)
                update_copyrights(package_name, license_id, data, ctx)
                lines.add(format_attribution_line(package_name, license_id, data['copyright'].get(license_id, '')))
            continue

        license_ids = set()
        for package_license in data['licenses']:
            package_license = package_license.strip('"')

            expanded_licenses = []
            for separator in (' and/or ', '/', ' OR ', ' or '):
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
                update_copyrights(package_name, license_id, data, ctx)
                lines.add(format_attribution_line(package_name, license_id, data['copyright'].get(license_id, '')))
        else:
            package_license_errors[package_name].append('no license information')

    if package_license_errors:
        for package_name, errors in package_license_errors.items():
            echo_info(package_name)
            for error in errors:
                echo_failure(error, indent=True)

        abort()

    extra_licenses_lines, any_errors = validate_extra_licenses()
    lines |= extra_licenses_lines
    lines |= ADDITIONAL_LICENSES

    lines = sorted(lines)
    header_line = "{}\n".format(','.join(HEADERS))
    lines = [header_line] + lines
    license_attribution_file = get_license_attribution_file()
    if sync:
        write_file_lines(license_attribution_file, lines)
        if any_errors:
            abort('Failed to write all extra licenses. Please fix any reported errors')
        else:
            echo_success('Success!')
    elif read_file_lines(license_attribution_file) != lines:
        echo_warning('Found diff between current file vs expected file:')
        difference = difflib.unified_diff(read_file_lines(license_attribution_file), lines)
        for item in difference:
            echo_warning(item)
        abort('Out of sync, run again with the --sync flag')
    elif any_errors:
        abort()
    else:
        echo_success('Licenses file is valid!')
