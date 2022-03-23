# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import copy
from collections import defaultdict

import click
import orjson
from aiohttp import request
from aiomultiprocess import Pool
from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import parse as parse_version

from ..constants import get_agent_requirements
from ..dependencies import (
    get_dependency_set,
    read_agent_dependencies,
    read_check_dependencies,
    update_agent_dependencies,
    update_check_dependencies,
    update_project_dependency,
)
from ..utils import get_normalized_dependency, normalize_project_name
from .console import CONTEXT_SETTINGS, abort, echo_failure, echo_info

# Dependencies to ignore when update dependencies
IGNORED_DEPS = {
    'psycopg2-binary',  # https://github.com/DataDog/integrations-core/pull/10456
    'ddtrace',  # https://github.com/DataDog/integrations-core/pull/9132
    'flup',  # https://github.com/DataDog/integrations-core/pull/1997
    # https://github.com/DataDog/integrations-core/pull/10105;
    # snowflake-connector-python 2.6.0 has requirement cryptography<4.0.0,>=2.5.0
    'cryptography',
    'dnspython',
}

# Dependencies for the downloader that are security-related and should be updated separately from the others
SECURITY_DEPS = {'in-toto', 'tuf', 'securesystemslib'}

SUPPORTED_PYTHON_MINOR_VERSIONS = {'2': '2.7', '3': '3.8'}


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage dependencies')
def dep():
    pass


@dep.command(context_settings=CONTEXT_SETTINGS, short_help='Pin a dependency for all checks that require it')
@click.argument('definition')
def pin(definition):
    """Pin a dependency for all checks that require it."""
    dependencies, errors = read_check_dependencies()

    if errors:
        for error in errors:
            echo_failure(error)

        abort()

    requirement = Requirement(definition)
    package = normalize_project_name(requirement.name)
    if package not in dependencies:
        abort(f'Unknown package: {package}')

    new_dependencies = copy.deepcopy(dependencies)
    python_versions = new_dependencies[package]
    checks = update_project_dependency(python_versions, definition)
    if new_dependencies == dependencies:
        abort('No dependency definitions to update')

    for check_name in sorted(checks):
        update_check_dependencies(check_name, new_dependencies)

    echo_info(f'Files updated: {len(checks)}')


@dep.command(
    context_settings=CONTEXT_SETTINGS, short_help="Combine all dependencies for the Agent's static environment"
)
def freeze():
    """Combine all dependencies for the Agent's static environment."""
    dependencies, errors = read_check_dependencies()

    if errors:
        for error in errors:
            echo_failure(error)

        abort()

    echo_info(f'Static file: {get_agent_requirements()}')
    update_agent_dependencies(dependencies)


@dep.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Update integrations' dependencies so that they match the Agent's static environment",
)
def sync():
    agent_dependencies, errors = read_agent_dependencies()

    if errors:
        for error in errors:
            echo_failure(error)
        abort()

    check_dependencies, check_errors = read_check_dependencies()

    if check_errors:
        for error in check_errors:
            echo_failure(error)
        abort()

    updated_checks = set()
    for name, python_versions in check_dependencies.items():
        check_dependency_definitions = get_dependency_set(python_versions)
        agent_dependency_definitions = get_dependency_set(agent_dependencies[name])

        if check_dependency_definitions != agent_dependency_definitions:
            for dependency_definition in agent_dependency_definitions:
                updated_checks.update(update_project_dependency(python_versions, dependency_definition))

    if not updated_checks:
        echo_info('All dependencies synced.')
        return

    for check_name in sorted(updated_checks):
        update_check_dependencies(check_name, check_dependencies)

    echo_info(f'Files updated: {len(updated_checks)}')


def filter_releases(releases):
    filtered_releases = []
    for version, artifacts in releases.items():
        parsed_version = parse_version(version)
        if not parsed_version.is_prerelease:
            filtered_releases.append((parsed_version, artifacts))

    return filtered_releases


def artifact_compatible_with_python(artifact, major_version):
    requires_python = artifact['requires_python']
    if requires_python is not None:
        return SpecifierSet(requires_python).contains(SUPPORTED_PYTHON_MINOR_VERSIONS[major_version])

    python_version = artifact['python_version']
    return f'py{major_version}' in python_version or f'cp{major_version}' in python_version


async def get_version_data(url):
    async with request('GET', url) as response:
        try:
            data = orjson.loads(await response.read())
        except Exception as e:
            raise type(e)(f'Error processing URL {url}: {e}')
        else:
            return data['info']['name'], data['releases']


async def scrape_version_data(urls):
    package_data = {}

    async with Pool() as pool:
        async for package_name, releases in pool.map(get_version_data, urls):
            latest_py2 = None
            latest_py3 = None

            versions = []
            for parsed_version, artifacts in reversed(sorted(filter_releases(releases))):
                version = str(parsed_version)
                versions.append(version)

                for artifact in artifacts:
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


@dep.command(context_settings=CONTEXT_SETTINGS, short_help='Automatically check for dependency updates')
@click.option('--sync', '-s', 'sync_dependencies', is_flag=True, help='Update the dependency definitions')
@click.option('--include-security-deps', '-i', is_flag=True, help="Attempt to update security dependencies")
@click.option('--batch-size', '-b', type=int, help='The maximum number of dependencies to upgrade if syncing')
@click.pass_context
def updates(ctx, sync_dependencies, include_security_deps, batch_size):
    ignore_deps = set(IGNORED_DEPS)
    if not include_security_deps:
        ignore_deps.update(SECURITY_DEPS)
    ignore_deps = {normalize_project_name(d) for d in ignore_deps}

    dependencies, errors = read_agent_dependencies()

    if errors:
        for error in errors:
            echo_failure(error)
        abort()

    api_urls = [f'https://pypi.org/pypi/{package}/json' for package in dependencies]
    package_data = asyncio.run(scrape_version_data(api_urls))
    package_data = {normalize_project_name(package_name): versions for package_name, versions in package_data.items()}

    new_dependencies = copy.deepcopy(dependencies)
    version_updates = defaultdict(lambda: defaultdict(set))
    updated_packages = set()
    for name, python_versions in sorted(new_dependencies.items()):
        if name in ignore_deps:
            continue
        elif batch_size is not None and len(updated_packages) >= batch_size:
            break

        new_python_versions = package_data[name]
        dropped_py2 = len(set(new_python_versions.values())) > 1
        for python_version, package_version in new_python_versions.items():
            dependency_definitions = python_versions[python_version]
            if not dependency_definitions or package_version is None:
                continue
            dependency_definition, checks = dependency_definitions.popitem()

            requirement = Requirement(dependency_definition)
            requirement.specifier = SpecifierSet(f'=={package_version}')
            if dropped_py2 and 'python_version' not in dependency_definition:
                python_marker = f'python_version {"<" if python_version == "py2" else ">"} "3.0"'
                if not requirement.marker:
                    requirement.marker = Marker(python_marker)
                else:
                    requirement.marker = Marker(f'{requirement.marker} and {python_marker}')

            new_dependency_definition = get_normalized_dependency(requirement)

            dependency_definitions[new_dependency_definition] = checks
            if dependency_definition != new_dependency_definition:
                version_updates[name][package_version].add(python_version)
                updated_packages.add(name)

    if sync_dependencies:
        if updated_packages:
            update_agent_dependencies(new_dependencies)
            ctx.invoke(sync)
            echo_info(f'Updated {len(updated_packages)} dependencies')
    else:
        if updated_packages:
            echo_failure(f"{len(updated_packages)} dependencies are out of sync:")
            for name, versions in version_updates.items():
                for package_version, python_versions in versions.items():
                    echo_failure(
                        f'{name} can be updated to version {package_version} '
                        f'on {" and ".join(sorted(python_versions))}'
                    )
            abort()
        else:
            echo_info('All dependencies are up to date')
