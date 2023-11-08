# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


def format_attribution_line(package_name, license_id, package_copyright):
    if ',' in package_copyright:
        package_copyright = f'"{package_copyright}"'

    return f'{package_name},PyPI,{license_id},{package_copyright}\n'


def update_copyrights(package_name, license_id, data, app):
    """
    Update package data with scraped copyright attributions.
    """
    from ddev.cli.validate import licenses_utils

    package_repo_overrides = app.repo.config.get('/overrides/dependencies/repo', {})
    gh_repo_url = package_repo_overrides.get(package_name) or data['home_page']
    created_date = '' if gh_repo_url is None else probe_github(gh_repo_url, app)

    url = collect_source_url(data)
    cp = scrape_copyright_data(url)
    if cp:
        data['copyright'][license_id] = cp

    if data['author'] and not data['copyright'].get(license_id):
        cp = 'Copyright {}{}'.format(created_date, data['author'])
        if license_id in licenses_utils.COPYRIGHT_ATTR_TEMPLATES:
            cp = licenses_utils.COPYRIGHT_ATTR_TEMPLATES[license_id].format(
                year=created_date, author=data['author'], package_name=package_name, license=license_id
            )
        data['copyright'][license_id] = cp


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


def scrape_copyright_data(url_path):
    """
    Scrapes each tarfile for copyright attributions.
    """
    import httpx

    with httpx.stream('GET', url_path, follow_redirects=True) as resp:
        resp.read()
        for fcontents in pick_file_generator(url_path)(resp):
            if cp := find_cpy(fcontents):
                return cp
    return None


def find_cpy(data):
    """
    Performs pattern matching on input data to find copyright attributions.
    Returns the copyright attribution if found.
    """
    import re

    from ddev.cli.validate import licenses_utils

    text = str(data, 'UTF-8')
    for line in text.splitlines():
        line = re.sub(r'.*#', '', line)
        line = line.strip()
        m = licenses_utils.COPYRIGHT_RE.search(line)
        if not m:
            continue
        cpy = m.group(0)
        # ignore a few spurious matches from license boilerplate
        if any(ign.match(cpy) for ign in licenses_utils.COPYRIGHT_IGNORE_RE):
            # if any(ign.match(cpy) for ign in get_copyright_ignore_re()):
            continue

        cpy = cpy.strip().rstrip(',')
        if cpy:
            return cpy


def get_extra_license_files(app):
    import os

    for path in app.repo.path.iterdir():
        if not os.path.isfile(os.path.join('', path, 'manifest.json')):
            continue
        extra_license_file = os.path.join('', path, '3rdparty-extra-LICENSE.csv')
        if os.path.isfile(extra_license_file):
            yield extra_license_file


def pick_file_generator(url):
    if url.endswith(".tar.gz"):
        return generate_from_tarball
    elif url.endswith(".whl"):
        return generate_from_wheel
    else:
        raise ValueError(f"Unknown type of archive based on this url: {url}")


def generate_from_tarball(response):
    import io
    import tarfile
    from contextlib import closing

    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r|gz") as archive:
        for tar_info in archive:
            if not (tar_info.islnk() or tar_info.issym()) and parse_license_path(tar_info.name):
                fh = archive.extractfile(tar_info)
                if fh is not None:
                    with closing(fh) as safe_fh:
                        yield safe_fh.read()


def generate_from_wheel(response):
    import io
    from zipfile import ZipFile

    with ZipFile(io.BytesIO(response.content)) as archive:
        for name in archive.namelist():
            if parse_license_path(name):
                with archive.open(name) as fh:
                    yield fh.read()


def parse_license_path(tar_file_name):
    """
    Parses filepath name and returns the filepath if it is a potential copyright attribution location.
    """
    from ddev.cli.validate import licenses_utils

    file_name_parts = tar_file_name.split("/")
    # Look at only the root-level files
    if len(file_name_parts) == 2:
        m = licenses_utils.COPYRIGHT_LOCATIONS_RE.search(file_name_parts[1])
        # m = get_copyright_locations_re().search(file_name_parts[1])
        if m:
            return file_name_parts[1]
    return None


def probe_github(url, app):
    """Probe GitHub API for package's repo creation date."""
    import re

    import httpx

    if url.endswith('/'):
        url = url[:-1]
    if 'github.com' not in url:
        return ''
    owner_repo = re.sub(r'.*github.com/', '', url)
    repo_api_url = f'https://api.github.com/repos/{owner_repo}'
    try:
        resp = app.github.client.get(repo_api_url, auth=get_auth_info(app), follow_redirects=True)
        resp.raise_for_status()
        created_date = resp.json().get('created_at', '')
    except httpx.HTTPError:
        created_date = ''
    return created_date[:4] + ' ' if created_date else created_date


def get_auth_info(config=None):
    """
    See if a personal access token was passed
    """
    import os

    gh_config = (config or {}).get('github', {})
    user = gh_config.get('user') or os.getenv('DD_GITHUB_USER')
    token = gh_config.get('token') or os.getenv('DD_GITHUB_TOKEN')
    if user and token:
        return user, token


def get_known_spdx_licenses(app):
    import orjson

    url = 'https://raw.githubusercontent.com/spdx/license-list-data/v3.13/json/licenses.json'
    response = app.github.client.get(url, follow_redirects=True)
    license_list = orjson.loads(response.content)['licenses']

    return {data['licenseId'] for data in license_list}


def extract_classifier_value(classifier):
    return classifier.split(' :: ')[-1]


def get_data(url, app):
    import orjson

    response = app.github.client.get(url, follow_redirects=True)
    return orjson.loads(response.content)


def scrape_license_data(urls, app):
    import concurrent.futures
    from collections import defaultdict

    package_data = defaultdict(
        lambda: {'copyright': {}, 'licenses': set(), 'classifiers': set(), 'home_page': None, 'author': None}
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(get_data, url, app): url for url in urls}
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


def read_license_file_rows(license_file):
    """
    Iterate over the rows of a `3rdparty-extra-LICENSE.csv` or `LICENSE-3rdparty.csv` file.
    """
    import csv

    with open(license_file, encoding='utf-8') as f:
        lines = f.readlines()
        f.seek(0)
        reader = csv.DictReader(f, delimiter=',')

        # Read header
        reader._fieldnames = reader.fieldnames

        for line_no, row in enumerate(reader, 2):
            # return the original line because it will be needed to append to the original file
            line = lines[line_no - 1]
            yield line_no, row, line


def validate_extra_licenses(app):
    """
    Validates extra third party licenses.

    An integration may use code from an outside source or origin that is not pypi-
    it will have a file in its check directory titled `3rdparty-extra-LICENSE.csv`
    """
    from ddev.cli.validate import licenses_utils

    lines = set()
    error_message = ""
    any_errors = False

    all_extra_licenses = get_extra_license_files(app)

    for license_file in all_extra_licenses:
        errors = False
        rows = read_license_file_rows(license_file)
        for line_no, row, line in rows:
            if None in row.values():
                errors = True
                any_errors = True
                error_message += f"{license_file}:{line_no} Has the wrong amount of columns\n"
                continue

            # all headers exist, no invalid headers
            all_keys = set(row)
            all_headers = set(licenses_utils.HEADERS)
            if all_keys != all_headers:
                invalid_headers = all_keys.difference(all_headers)
                if invalid_headers:
                    error_message += f'{license_file}:{line_no} Invalid column {invalid_headers}\n'

                missing_headers = all_headers.difference(all_keys)
                if missing_headers:
                    error_message += f'{license_file}:{line_no} Missing columns {missing_headers}\n'

                errors = True
                any_errors = True
                continue

            license_type = row['License']

            if license_type not in licenses_utils.VALID_LICENSES:
                errors = True
                any_errors = True
                error_message += f'{license_file}:{line_no} Invalid license type {license_type}\n'
                continue
            if not errors:
                lines.add(line)

    return lines, any_errors, error_message


def read_file_lines(file, encoding='utf-8'):
    with open(file, 'r', encoding=encoding) as f:
        return f.readlines()


@click.command(short_help='Validate third-party license list')
@click.option('--sync', '-s', is_flag=True, help='Generate the `LICENSE-3rdparty.csv` file')
@click.pass_obj
def licenses(app: Application, sync: bool):
    import difflib
    import os
    from collections import defaultdict

    from tqdm import tqdm

    from ddev.cli.validate import licenses_utils

    if app.repo.name != 'core':
        app.display_info(f"License validation is only available for repo `core`, skipping for repo `{app.repo.name}`")
        app.abort()

    from packaging.requirements import InvalidRequirement, Requirement

    validation_tracker = app.create_validation_tracker('Licenses')

    # Validate that all values in the constants (EXPLICIT_LICENSES and
    # PACKAGE_REPO_OVERRIDES) appear in agent_requirements.in file
    errors = False
    error_message = ""

    agent_requirements_path = app.repo.agent_requirements
    validation_branch = (str(agent_requirements_path.relative_to(app.repo.path)),)
    if not os.path.isfile(agent_requirements_path):
        error_message = "Requirements file is not found. Out of sync, run 'ddev validate licenses --sync'"
        validation_tracker.error(validation_branch, message=error_message)
        validation_tracker.display()
        app.abort()

    packages_set = set()
    packages = defaultdict(set)
    with open(agent_requirements_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f.readlines()):
            try:
                requirement = Requirement(line.strip())
                packages_set.add(requirement.name)
                packages[requirement.name].add(str(requirement.specifier)[2:])
            except InvalidRequirement as e:
                rel_file = os.path.basename(agent_requirements_path)
                temp_line = i + 1
                error_message += f"Detected InvalidRequirement error in {rel_file}:{temp_line} {e}\n"
                errors = True
        if errors:
            validation_tracker.error(validation_branch, message=error_message)
            validation_tracker.display()
            app.abort()

    for dependency_override, constant_name in [('licenses', 'EXPLICIT_LICENSES'), ('repo', 'PACKAGE_REPO_OVERRIDES')]:
        for name in app.repo.config.get(f'/overrides/dependencies/{dependency_override}', {}):
            if name.lower() not in packages_set:
                errors = True
                error_message += f"{constant_name} contains additional package not in agent requirements: {name}\n"

    if errors:
        validation_tracker.error(
            (constant_name, name),
            message=error_message,
        )
        validation_tracker.display()
        app.abort()

    api_urls = []
    for package, versions in packages.items():
        for version in versions:
            api_urls.append(f'https://pypi.org/pypi/{package}/{version}/json')

    package_data = scrape_license_data(api_urls, app)
    known_spdx_licenses = {license_id.lower(): license_id for license_id in get_known_spdx_licenses(app)}

    package_license_errors = defaultdict(list)

    app.display_info("Validating main licenses.")
    lines = set()
    for (package_name, _version), data in tqdm(sorted(package_data.items()), desc="Generating CSV lines.", unit="pkgs"):
        explicit_licenses = app.repo.config.get('/overrides/dependencies/licenses', {})
        if package_name in explicit_licenses:
            for license_id in sorted(explicit_licenses[package_name]):
                data['licenses'].add(license_id)
                update_copyrights(package_name, license_id, data, app)
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
                if normalized_license in licenses_utils.IGNORED_LICENSES:
                    continue
                elif normalized_license in licenses_utils.KNOWN_LICENSES:
                    license_ids.add(licenses_utils.KNOWN_LICENSES[normalized_license])
                elif normalized_license in known_spdx_licenses:
                    license_ids.add(known_spdx_licenses[normalized_license])
                else:
                    license_ids.add(expanded_license)
                    package_license_errors[package_name].append(f'unknown license: {expanded_license}')

        for classifier in data['classifiers']:
            if classifier in licenses_utils.KNOWN_CLASSIFIERS:
                license_ids.add(licenses_utils.KNOWN_CLASSIFIERS[classifier])
            elif classifier in licenses_utils.CLASSIFIER_TO_HIGHEST_SPDX:
                license_ids.add(licenses_utils.CLASSIFIER_TO_HIGHEST_SPDX[classifier])
            else:
                package_license_errors[package_name].append(f'unknown classifier: {classifier}')

        if license_ids:
            for license_id in sorted(license_ids):
                update_copyrights(package_name, license_id, data, app)
                lines.add(format_attribution_line(package_name, license_id, data['copyright'].get(license_id, '')))
        else:
            package_license_errors[package_name].append('no license information')
    if package_license_errors:
        error_message = ''
        for package_name, package_errors in package_license_errors.items():
            for error in package_errors:
                error_message += error + '\n'
            validation_tracker.error((package_name), message=error_message)

        validation_tracker.display()
        app.abort()

    app.display_info("Validating extra licenses.")
    extra_licenses_lines, any_errors, error_msg_temp = validate_extra_licenses(app)
    error_message += error_msg_temp
    lines |= extra_licenses_lines
    lines |= licenses_utils.ADDITIONAL_LICENSES

    sorted_lines = sorted(lines)
    header_line = "{}\n".format(','.join(licenses_utils.HEADERS))
    sorted_lines = [header_line] + sorted_lines
    license_attribution_file = app.repo.path / 'LICENSE-3rdparty.csv'
    if sync:
        with open(license_attribution_file, 'w', encoding='utf-8') as f:
            f.writelines(str(line) for line in sorted_lines)
        if any_errors:
            error_message += 'Failed to write all extra licenses. Please fix any reported errors\n'
            validation_tracker.error(validation_branch, message=error_message)
            validation_tracker.display()
            app.abort()
        else:
            validation_tracker.success()
            validation_tracker.display()

    elif any_errors:
        validation_tracker.error(validation_branch, message=error_message)
        validation_tracker.display()
        app.abort()
    elif read_file_lines(license_attribution_file) != sorted_lines:
        warning_message = 'Found diff between current file vs expected file:\n'
        difference = difflib.unified_diff(read_file_lines(license_attribution_file), sorted_lines)
        for item in difference:
            warning_message += item + '\n'

        validation_tracker.warning(validation_branch, message=warning_message)
        validation_tracker.error(validation_branch, message='Out of sync, run again with the --sync flag')
        validation_tracker.display()
        app.abort()
    else:
        validation_tracker.success()
        validation_tracker.display()
