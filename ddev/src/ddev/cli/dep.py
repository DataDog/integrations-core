# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import copy
from collections import defaultdict

import click
import httpx
import orjson
from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from ddev.repo.constants import PYTHON_VERSION

# Dependencies to ignore when update dependencies
IGNORED_DEPS = {
    'ddtrace',  # https://github.com/DataDog/integrations-core/pull/9132
    'foundationdb',  # Breaking datadog_checks_base tests
    'pyasn1',  # https://github.com/pyasn1/pyasn1/issues/52
    'pysnmp',  # Breaking snmp tests
    'aerospike',  # v8+ breaks agent build.
    # We need pydantic 2.0.2 for the rpm x64 agent build (see https://github.com/DataDog/datadog-agent/pull/18303)
    'pydantic',
    # https://github.com/DataDog/integrations-core/pull/16080
    'lxml',
    # We need to keep an `oracledb` version that uses the same version of odpi that is used in godror in the agent repo.
    # Somehow we do not load the right version. Until we find out how and why, we need to keep both
    # libs in sync with the same version of odpi.
    'oracledb',
    # We're not ready to switch to v3 of the postgres library, see:
    # https://github.com/DataDog/integrations-core/pull/15859
    'psycopg2-binary',
    # orjson ... requires rustc 1.65+, but the latest we can have (thanks CentOS 6) is 1.62.
    # We get the following error when compiling orjson on Centos 6:
    # error: package `associative-cache v2.0.0` cannot be built because it requires rustc 1.65 or newer,
    # while the currently active rustc version is 1.62.0-nightly
    # Here's orjson switching to rustc 1.65:
    # https://github.com/ijl/orjson/commit/ce9bae876657ed377d761bf1234b040e2cc13d3c
    'orjson',
    # 2.4.10 is broken on py2 and they did not yank the version
    'rethinkdb',
    # cryptography>=42 requires rust>=1.63.0. We have rust 1.62 on centos 6
    # https://github.com/DataDog/datadog-agent/pull/22268
    'cryptography',
    # Brings urllib 2.0.7 which breaks `test_uds_request` in the base check
    # https://github.com/kubernetes-client/python/pull/2131
    'kubernetes',
}

# Dependencies for the downloader that are security-related and should be updated separately from the others
SECURITY_DEPS = {'in-toto', 'tuf', 'securesystemslib'}

SUPPORTED_PYTHON_MINOR_VERSIONS = {'2': '2.7', '3': PYTHON_VERSION}


@click.group(short_help='Manage dependencies')
def dep():
    pass


@dep.command(short_help='Pin a dependency for all checks that require it')
@click.argument('definition')
@click.pass_obj
def pin(app, definition):
    """Pin a dependency for all checks that require it."""
    dependencies, errors = read_check_dependencies(app.repo)

    if errors:
        for error in errors:
            app.display_error(error)

        app.abort()

    requirement = Requirement(definition)
    package = canonicalize_name(requirement.name)
    if package not in dependencies:
        app.abort(f'Unknown package: {package}')

    new_dependencies = copy.deepcopy(dependencies)
    python_versions = new_dependencies[package]
    checks = update_project_dependency(python_versions, definition)
    if new_dependencies == dependencies:
        app.abort('No dependency definitions to update')

    for check_name in sorted(checks):
        update_check_dependencies(app.repo.integrations.get(check_name), new_dependencies)

    app.display_info(f'Files updated: {len(checks)}')


@dep.command(short_help="Combine all dependencies for the Agent's static environment")
@click.pass_obj
def freeze(app):
    """Combine all dependencies for the Agent's static environment."""
    dependencies, errors = read_check_dependencies(app.repo)

    if errors:
        for error in errors:
            app.display_error(error)

        app.abort()

    app.display_info(f'Static file: {app.repo.agent_requirements}')
    update_agent_dependencies(app.repo, dependencies)


@dep.command(
    short_help="Update integrations' dependencies so that they match the Agent's static environment",
)
@click.pass_obj
def sync(app):
    agent_dependencies, errors = read_agent_dependencies(app.repo)

    if errors:
        for error in errors:
            app.display_error(error)
        app.abort()

    check_dependencies, check_errors = read_check_dependencies(app.repo)

    if check_errors:
        for error in check_errors:
            app.display_error(error)
        app.abort()

    updated_checks = set()
    for name, python_versions in check_dependencies.items():
        check_dependency_definitions = get_dependency_set(python_versions)
        agent_dependency_definitions = get_dependency_set(agent_dependencies[name])

        if check_dependency_definitions != agent_dependency_definitions:
            for dependency_definition in agent_dependency_definitions:
                updated_checks.update(update_project_dependency(python_versions, dependency_definition))

    if not updated_checks:
        app.display_info('All dependencies synced.')
        return

    for check_name in sorted(updated_checks):
        update_check_dependencies(app.repo.integrations.get(check_name), check_dependencies)

    app.display_info(f'Files updated: {len(updated_checks)}')


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


@dep.command(short_help='Automatically check for dependency updates')
@click.option('--sync', '-s', 'sync_dependencies', is_flag=True, help='Update the dependency definitions')
@click.option('--include-security-deps', '-i', is_flag=True, help="Attempt to update security dependencies")
@click.option('--batch-size', '-b', type=int, help='The maximum number of dependencies to upgrade if syncing')
@click.pass_context
@click.pass_obj
def updates(app, ctx, sync_dependencies, include_security_deps, batch_size):
    ignore_deps = set(IGNORED_DEPS)
    if not include_security_deps:
        ignore_deps.update(SECURITY_DEPS)
    ignore_deps = {canonicalize_name(d) for d in ignore_deps}

    dependencies, errors = read_agent_dependencies(app.repo)

    if errors:
        for error in errors:
            app.display_error(error)
        app.abort()

    api_urls = [f'https://pypi.org/pypi/{package}/json' for package in dependencies]
    package_data = scrape_version_data(api_urls)
    package_data = {canonicalize_name(package_name): versions for package_name, versions in package_data.items()}

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
            update_agent_dependencies(app.repo, new_dependencies)
            ctx.invoke(sync)
            app.display_info(f'Updated {len(updated_packages)} dependencies')
    else:
        if updated_packages:
            app.display_error(f"{len(updated_packages)} dependencies are out of sync:")
            for name, versions in version_updates.items():
                for package_version, python_versions in versions.items():
                    app.display_error(
                        f'{name} can be updated to version {package_version} '
                        f'on {" and ".join(sorted(python_versions))}'
                    )
            app.abort()
        else:
            app.display_info('All dependencies are up to date')


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
