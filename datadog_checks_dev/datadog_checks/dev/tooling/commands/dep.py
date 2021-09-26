# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from collections import defaultdict

import click
import orjson
from aiohttp import request
from aiomultiprocess import Pool
from packaging.markers import InvalidMarker, Marker
from packaging.specifiers import SpecifierSet

from ...fs import read_file_lines, write_file_lines
from ..constants import get_agent_requirements
from ..dependencies import read_agent_dependencies, read_check_dependencies
from ..utils import get_check_req_file, get_valid_checks
from .console import CONTEXT_SETTINGS, abort, echo_failure, echo_info
from .validate.licenses import extract_classifier_value

# Dependencies to ignore when update dependencies
IGNORED_DEPS = {'psycopg2-binary'}


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage dependencies')
def dep():
    pass


@dep.command(context_settings=CONTEXT_SETTINGS, short_help='Pin a dependency for all checks that require it')
@click.argument('package')
@click.argument('version')
@click.option('--marker', '-m', help='Environment marker to use')
def pin(package, version, marker):
    """Pin a dependency for all checks that require it. This can
    also resolve transient dependencies.

    Setting the version to `none` will remove the package. You can
    specify an unlimited number of additional checks to apply the
    pin for via arguments.
    """
    if marker is not None:
        try:
            marker = Marker(marker)
        except InvalidMarker as e:
            abort(f'Invalid marker: {e}')

    dependencies, errors = read_check_dependencies()

    if errors:
        for error in errors:
            echo_failure(error)

        abort()

    package = package.lower()
    if package not in dependencies:
        abort(f'Unknown package: {package}')

    files_to_update = defaultdict(list)
    files_updated = 0

    versions = dependencies[package]
    for dependency_definitions in versions.values():
        for dependency_definition in dependency_definitions:
            files_to_update[dependency_definition.file_path].append(dependency_definition)

    for file_path, dependency_definitions in sorted(files_to_update.items()):
        old_lines = read_file_lines(file_path)

        new_lines = old_lines.copy()

        for dependency_definition in dependency_definitions:
            requirement = dependency_definition.requirement
            if marker != requirement.marker:
                continue

            requirement.specifier = SpecifierSet(f'=={version}')
            new_lines[dependency_definition.line_number] = f'{requirement}\n'

        if new_lines != old_lines:
            files_updated += 1
            write_file_lines(file_path, new_lines)

    if not files_updated:
        abort('No dependency definitions to update')

    echo_info(f'Files updated: {files_updated}')


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

    static_file = get_agent_requirements()

    echo_info(f'Static file: {static_file}')

    data = sorted(
        (
            (dependency_definition.name, str(dependency_definition.requirement).lower())
            for versions in dependencies.values()
            for dependency_definitions in versions.values()
            for dependency_definition in dependency_definitions
        ),
        key=lambda d: d[0],
    )
    lines = sorted(set(f'{d[1]}\n' for d in data))

    write_file_lines(static_file, lines)


@dep.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Update integrations' dependencies so that they match the Agent's static environment",
)
def sync():
    all_agent_dependencies, errors = read_agent_dependencies()

    if errors:
        for error in errors:
            echo_failure(error)
        abort()

    files_updated = 0
    checks = sorted(get_valid_checks())
    for check_name in checks:
        check_dependencies, check_errors = read_check_dependencies(check=check_name)

        if check_errors:
            for error in check_errors:
                echo_failure(error)
            abort()

        deps_to_update = {
            check_dependency_definition: agent_dep_version
            for check_dependency_name, check_dependency_definitions in check_dependencies.items()
            for version, dependency_definitions in check_dependency_definitions.items()
            for check_dependency_definition in dependency_definitions
            for agent_dep_version, agent_dependency_definitions in all_agent_dependencies[check_dependency_name].items()
            for agent_dependency_definition in agent_dependency_definitions
            # look for the dependency with the same marker and name since the version can be different
            if check_dependency_definition.same_name_marker(agent_dependency_definition)
            and version != agent_dep_version
        }

        if deps_to_update:
            files_updated += 1
            check_req_file = get_check_req_file(check_name)
            old_lines = read_file_lines(check_req_file)
            new_lines = old_lines.copy()

            for dependency_definition, new_version in deps_to_update.items():
                dependency_definition.requirement.specifier = new_version
                new_lines[dependency_definition.line_number] = f'{dependency_definition.requirement}\n'

            write_file_lines(check_req_file, new_lines)

    if not files_updated:
        echo_info('All dependencies synced.')

    echo_info(f'Files updated: {files_updated}')


async def get_version_data(url):
    async with request('GET', url) as response:
        try:
            info = orjson.loads(await response.read())['info']
        except Exception as e:
            raise type(e)(f'Error processing URL {url}: {e}')
        else:
            return (
                info['name'],
                info['version'],
                {
                    extract_classifier_value(c)
                    for c in info['classifiers']
                    if c.startswith('Programming Language :: Python ::')
                },
            )


async def scrape_version_data(urls):
    package_data = defaultdict(lambda: {'version': '', 'classifiers': set()})

    async with Pool() as pool:
        async for package_name, package_version, version_classifiers in pool.map(get_version_data, urls):
            data = package_data[package_name]
            if package_version:
                data['version'] = package_version

            data['classifiers'].update(version_classifiers)

    return package_data


def is_version_compatible(marker, supported_versions):
    """
    Determines if any of the given versions are compatible with the given marker
    """
    os_markers = ['darwin', 'win32', 'linux', 'aix']
    is_compatible = False

    if marker is None:
        # manually set marker since if there's none the dependency should work on all environments
        marker = Marker('python_version > "2.0"')

    if len(supported_versions) == 0:
        # if there are no classifiers then assume it works on all Python versions
        is_compatible = True

    for python_version in supported_versions:
        has_match = False

        for os in os_markers:
            env = {'python_version': python_version, 'sys_platform': os}
            # override system python version and sys platform to evaluate whether the version is compatible
            has_match = marker.evaluate(environment=env)
            is_compatible = is_compatible or has_match

    return is_compatible


@dep.command(context_settings=CONTEXT_SETTINGS, short_help='Automatically check for dependency updates')
@click.option('--sync', '-s', is_flag=True, help='Update the `agent_requirements.in` file')
@click.option(
    '--check-python-classifiers',
    '-s',
    is_flag=True,
    help="""Only flag a dependency as needing an update if the newest version has python classifiers matching the marker.
    NOTE: Some packages may not have proper classifiers.""",
)
def updates(sync, check_python_classifiers):

    all_agent_dependencies, errors = read_agent_dependencies()

    api_urls = []
    for package in all_agent_dependencies.keys():
        api_urls.append(f'https://pypi.org/pypi/{package}/json')

    package_data = asyncio.run(scrape_version_data(api_urls))
    package_data = {
        package_name.lower().replace('_', '-'): package_info for package_name, package_info in package_data.items()
    }

    deps_to_update = {
        agent_dependency_definition: package_data[package]['version']
        for package, package_dependency_definitions in all_agent_dependencies.items()
        if package not in IGNORED_DEPS
        for agent_dep_version, agent_dependency_definitions in package_dependency_definitions.items()
        for agent_dependency_definition in agent_dependency_definitions
        if str(agent_dep_version)[2:] != package_data[package]['version']
        and (
            not check_python_classifiers
            or is_version_compatible(
                agent_dependency_definition.requirement.marker,
                package_data[package]['classifiers'],
            )
        )
    }

    if sync:
        static_file = get_agent_requirements()
        if deps_to_update:
            old_lines = read_file_lines(static_file)
            new_lines = old_lines.copy()

            for dependency_definition, new_version in deps_to_update.items():
                dependency_definition.requirement.specifier = f'=={new_version}'
                new_lines[dependency_definition.line_number] = f'{dependency_definition.requirement}\n'

            write_file_lines(static_file, new_lines)
            echo_info(f'Updated {len(deps_to_update.keys())} dependencies in `agent_requirements.in`')
    else:
        if deps_to_update:
            echo_failure(f"{len(deps_to_update.keys())} Dependencies are out of sync:")
            for dependency_definition, version in deps_to_update.items():
                echo_failure(f"Dependency {dependency_definition.requirement} can be updated to version {version}")
        else:
            echo_info('All dependencies are up to date')
