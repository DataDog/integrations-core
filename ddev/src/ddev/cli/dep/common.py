# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from collections import defaultdict

import httpx
import orjson
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from ddev.repo.constants import PYTHON_VERSION

SUPPORTED_PYTHON_MINOR_VERSIONS = {'2': '2.7', '3': PYTHON_VERSION}


def get_dependency_set(python_versions):
    return {
        dependency_definition
        for dependency_definitions in python_versions.values()
        for dependency_definition in dependency_definitions
    }


def read_agent_dependencies(repo):
    dependencies = create_dependency_data()
    errors = []

    load_dependency_data_from_requirements(repo.agent_requirements, dependencies, errors)

    return dependencies, errors


def read_check_dependencies(repo, integrations=None):
    dependencies = create_dependency_data()
    errors = []

    if isinstance(integrations, list):
        integrations = [repo.integrations.get(integration) for integration in integrations]
    elif integrations is None:
        integrations = list(repo.integrations.iter_shippable('all'))
    else:
        integrations = [repo.integrations.get(integrations)]

    for integration in sorted(integrations, key=lambda x: x.name):
        if integration.name in {'datadog_checks_dev', 'datadog_checks_tests_helper', 'ddev'}:
            continue

        if integration.is_package:
            load_dependency_data_from_metadata(integration, dependencies, errors)

    return dependencies, errors


def update_agent_dependencies(repo, dependencies):
    lines = sorted(
        f'{dependency_definition}\n'
        for python_versions in dependencies.values()
        for dependency_definition in get_dependency_set(python_versions)
    )

    repo.agent_requirements.write_text(''.join(lines))


def update_check_dependencies(integration, dependencies):
    project_data = integration.project_metadata
    optional_dependencies = project_data['project'].get('optional-dependencies', {})

    updated = False
    for old_dependencies in optional_dependencies.values():
        new_dependencies = defaultdict(set)

        for old_dependency in old_dependencies:
            old_requirement = Requirement(old_dependency)
            name = canonicalize_name(old_requirement.name)
            if name not in dependencies:
                new_dependencies[name].add(old_dependency)
                continue

            for dependency_set in dependencies[name].values():
                for dep in dependency_set:
                    new_dependencies[name].add(dep)

        new_dependencies = sorted(d for dep_set in new_dependencies.values() for d in dep_set)
        if new_dependencies != old_dependencies:
            updated = True
            old_dependencies[:] = new_dependencies

    if updated:
        import tomli_w

        (integration.path / 'pyproject.toml').write_text(tomli_w.dumps(project_data))

    return updated


def create_dependency_data():
    # Structure:
    # dependency name ->
    #   Python major version ->
    #     dependency definition -> set of checks with definition
    return defaultdict(lambda: {'py2': defaultdict(set), 'py3': defaultdict(set)})


def load_dependency_data_from_requirements(req_file, dependencies, errors, check_name=None):
    for line in req_file.stream_lines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        try:
            req = Requirement(line)
        except InvalidRequirement as e:
            import os

            errors.append(f'File `{os.path.basename(req_file)}` has an invalid dependency: `{line}`\n{e}')
            continue

        project = dependencies[canonicalize_name(req.name)]
        dependency = get_normalized_dependency(req)
        set_project_dependency(project, dependency, check_name)


def load_dependency_data_from_metadata(integration, dependencies, errors):
    project_data = integration.project_metadata

    optional_dependencies = project_data['project'].get('optional-dependencies', {})

    for check_dependencies in optional_dependencies.values():
        for check_dependency in check_dependencies:
            try:
                req = Requirement(check_dependency)
            except InvalidRequirement as e:
                errors.append(
                    f'File `{integration.name}/pyproject.toml` has an invalid dependency: `{check_dependency}`\n{e}'
                )
                continue

            project = dependencies[canonicalize_name(req.name)]
            dependency = get_normalized_dependency(req)
            set_project_dependency(project, dependency, integration.name)


def set_project_dependency(project, dependency, check_name):
    if 'python_version <' in dependency:
        project['py2'][dependency].add(check_name)
    elif 'python_version >' in dependency:
        project['py3'][dependency].add(check_name)
    else:
        project['py2'][dependency].add(check_name)
        project['py3'][dependency].add(check_name)


def update_project_dependency(project, dependency):
    if 'python_version <' in dependency:
        project['py2'][dependency] = project['py2'].popitem()[1]
        return project['py2'][dependency]
    elif 'python_version >' in dependency:
        project['py3'][dependency] = project['py3'].popitem()[1]
        return project['py3'][dependency]
    else:
        project['py2'][dependency] = project['py2'].popitem()[1]
        project['py3'][dependency] = project['py3'].popitem()[1]
        return project['py2'][dependency] | project['py3'][dependency]


def get_normalized_dependency(requirement):
    requirement.name = canonicalize_name(requirement.name)

    if requirement.specifier:
        requirement.specifier = SpecifierSet(str(requirement.specifier).lower())

    if requirement.extras:
        requirement.extras = {canonicalize_name(extra) for extra in requirement.extras}

    # All TOML writers use double quotes, so allow direct writing or copy/pasting to avoid escaping
    return str(requirement).replace('"', "'")


def filter_releases(releases):
    filtered_releases = []
    for version, artifacts in releases.items():
        try:
            parsed_version = Version(version)
        except InvalidVersion:
            continue

        if not parsed_version.is_prerelease:
            filtered_releases.append((parsed_version, artifacts))

    return filtered_releases


def artifact_compatible_with_python(artifact, major_version):
    requires_python = artifact['requires_python']
    if requires_python is not None:
        try:
            specifiers = SpecifierSet(requires_python)
        except InvalidSpecifier:
            return False

        return specifiers.contains(SUPPORTED_PYTHON_MINOR_VERSIONS[major_version])

    python_version = artifact['python_version']
    return f'py{major_version}' in python_version or f'cp{major_version}' in python_version


async def get_version_data(client, url):
    try:
        response = await client.get(url)
        data = orjson.loads(response.text)
    except Exception as e:
        raise RuntimeError(f'Error processing URL {url}') from e

    return data['info']['name'], data['releases']


async def fetch_versions(urls):
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(*(get_version_data(client, url) for url in urls))


def scrape_version_data(urls):
    package_data = {}

    for package_name, releases in asyncio.run(fetch_versions(urls)):
        latest_py2 = None
        latest_py3 = None

        versions = []
        for parsed_version, artifacts in sorted(filter_releases(releases), reverse=True):
            version = str(parsed_version)
            versions.append(version)

            for artifact in artifacts:
                if artifact.get("yanked", False):
                    continue

                if latest_py2 is None and artifact_compatible_with_python(artifact, '2'):
                    latest_py2 = version
                if latest_py3 is None and artifact_compatible_with_python(artifact, '3'):
                    latest_py3 = version

            if latest_py2 is not None and latest_py3 is not None:
                break
        else:
            # Package only released source distributions
            if latest_py2 is None and latest_py3 is None:
                latest_py2 = latest_py3 = versions[0]

        package_data[package_name] = {'py2': latest_py2, 'py3': latest_py3}

    return package_data
