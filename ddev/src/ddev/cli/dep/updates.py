# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from collections import defaultdict

import click
from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from ddev.cli.dep import sync
from ddev.cli.dep.common import (
    get_normalized_dependency,
    read_agent_dependencies,
    scrape_version_data,
    update_agent_dependencies,
)


@click.command(short_help='Automatically check for dependency updates')
@click.option('--sync', '-s', 'sync_dependencies', is_flag=True, help='Update the dependency definitions')
@click.option('--include-security-deps', '-i', is_flag=True, help="Attempt to update security dependencies")
@click.option('--batch-size', '-b', type=int, help='The maximum number of dependencies to upgrade if syncing')
@click.pass_context
@click.pass_obj
def updates(app, ctx, sync_dependencies, include_security_deps, batch_size):
    ignore_deps = set(app.repo.config.get('/overrides/dep/updates/exclude', []))

    if not include_security_deps:
        ignore_deps.update(set(app.repo.config.get('/overrides/dep/updates/security_deps', [])))
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
