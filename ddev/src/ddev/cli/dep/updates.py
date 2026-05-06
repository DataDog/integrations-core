# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from collections import defaultdict

import click
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
from ddev.utils.fs import Path


@click.command(short_help='Automatically check for dependency updates')
@click.option('--sync', '-s', 'sync_dependencies', is_flag=True, help='Update the dependency definitions')
@click.option('--include-security-deps', '-i', is_flag=True, help="Attempt to update security dependencies")
@click.option('--batch-size', '-b', type=int, help='The maximum number of dependencies to upgrade if syncing')
@click.option(
    '--report',
    is_flag=False,
    flag_value='',
    default=None,
    metavar='PATH',
    help='Write a dependency update report to PATH, or omit PATH to print to screen.',
)
@click.option(
    '--report-type',
    type=click.Choice(['json', 'markdown']),
    default='json',
    show_default=True,
    help='Format of the report file (only applies when a PATH is given).',
)
@click.pass_context
@click.pass_obj
def updates(app, ctx, sync_dependencies, include_security_deps, batch_size, report, report_type):
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
    report_entries: list[dict] = []
    for name, python_versions in sorted(new_dependencies.items()):
        if name in ignore_deps:
            continue
        elif batch_size is not None and len(updated_packages) >= batch_size:
            break

        python_version = 'py3'
        package_version = package_data[name][python_version]
        dependency_definitions = python_versions[python_version]
        if not dependency_definitions or package_version is None:
            continue
        dependency_definition, checks = dependency_definitions.popitem()

        requirement = Requirement(dependency_definition)
        requirement.specifier = SpecifierSet(f'=={package_version}')

        new_dependency_definition = get_normalized_dependency(requirement)

        dependency_definitions[new_dependency_definition] = checks
        if dependency_definition != new_dependency_definition:
            version_updates[name][package_version].add(python_version)
            updated_packages.add(name)
            if report is not None:
                report_entries.append(
                    {
                        'package': name,
                        'old_version': str(Requirement(dependency_definition).specifier).lstrip('='),
                        'new_version': str(package_version),
                    }
                )

    if report is None:
        pass
    elif report == '':
        _print_table_report(app, report_entries)
    elif report_type == 'json':
        _write_json_report(report_entries, report)
    else:
        _write_markdown_report(report_entries, report)

    if sync_dependencies:
        if updated_packages:
            update_agent_dependencies(app.repo, new_dependencies)
            ctx.invoke(sync)
            app.display_info(f'Updated {len(updated_packages)} dependencies')
    elif updated_packages:
        app.display_error(f"{len(updated_packages)} dependencies are out of sync:")
        for name, versions in version_updates.items():
            for package_version, python_versions in versions.items():
                app.display_error(
                    f'{name} can be updated to version {package_version} on {" and ".join(sorted(python_versions))}'
                )
        app.abort()
    else:
        app.display_info('All dependencies are up to date')


def _print_table_report(app, entries: list[dict]) -> None:
    sorted_entries = sorted(entries, key=lambda e: e['package'])
    if not sorted_entries:
        app.display_info('No dependency version changes detected.')
        return
    columns = {
        'Package': {i: e['package'] for i, e in enumerate(sorted_entries)},
        'Old Version': {i: e['old_version'] for i, e in enumerate(sorted_entries)},
        'New Version': {i: e['new_version'] for i, e in enumerate(sorted_entries)},
    }
    app.display_table('Dependency Bumps', columns, show_lines=True)


def _write_json_report(entries: list[dict], path: str) -> None:
    import json

    Path(path).write_text(json.dumps(sorted(entries, key=lambda e: e['package']), indent=2))


def _write_markdown_report(entries: list[dict], path: str) -> None:
    if sorted_entries := sorted(entries, key=lambda e: e['package']):
        lines = [
            '### Dependency Bumps',
            '',
            '| Package | Old Version | New Version |',
            '|---------|-------------|-------------|',
        ]
        lines.extend(f"| {e['package']} | {e['old_version']} | {e['new_version']} |" for e in sorted_entries)
        content = '\n'.join(lines)
    else:
        content = '_No dependency version changes detected._'
    Path(path).write_text(content)
