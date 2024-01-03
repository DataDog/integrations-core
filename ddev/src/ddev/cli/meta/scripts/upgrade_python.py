# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import click

from ddev.integration.core import Integration

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.src.ddev.validation.tracker import ValidationTracker


@click.command('upgrade-python', short_help='Upgrade the Python version throughout the repository')
@click.argument('version')
@click.pass_obj
def upgrade_python(app: Application, version: str):
    """Upgrade the Python version of all test environments.

    \b
    `$ ddev meta scripts upgrade-python 3.11`
    """

    from ddev.repo.constants import PYTHON_VERSION as old_version

    tracker = app.create_validation_tracker('Python upgrades')

    for target in integrations(app):
        update_hatch_file(app, target.path, version, old_version, tracker)
        update_pyproject_file(target, version, old_version, tracker)
        update_setup_file(target, version, old_version, tracker)

    update_ci_files(app, version, old_version, tracker)

    if app.repo.name == 'core':
        update_ddev_pyproject_file(app, version, old_version, tracker)
        update_constants_file(app, version, old_version, tracker)
        update_ddev_template_files(app, version, old_version, tracker)
        app.display_warning("Documentation files have not been updated. Please modify them manually.")

    tracker.display()

    if tracker.errors:  # no cov
        app.abort()


def integrations(app):
    extra_integrations = []

    if app.repo.name == 'core':
        names = ["datadog_checks_dependency_provider"]
        extra_integrations = [Integration(app.repo.path / name, app.repo.path, app.repo.config) for name in names]

    return itertools.chain(app.repo.integrations.iter_packages(['all']), extra_integrations)


def update_ci_files(app: Application, new_version: str, old_version: str, tracker: ValidationTracker):
    for file in (app.repo.path / ".github" / "workflows").glob("*.yml"):
        old_content = new_content = file.read_text()

        for pattern in ("python-version: '{}'", 'PYTHON_VERSION: "{}"', "'{}'"):
            if pattern.format(old_version) in new_content:
                new_content = new_content.replace(pattern.format(old_version), pattern.format(new_version))

        if old_content != new_content:
            file.write_text(new_content)
            tracker.success()


def update_ddev_template_files(app: Application, new_version: str, old_version: str, tracker: ValidationTracker):
    for check_type in ("check", "jmx", "logs"):
        folder_path = (
            app.repo.path
            / 'datadog_checks_dev'
            / 'datadog_checks'
            / 'dev'
            / 'tooling'
            / 'templates'
            / 'integration'
            / check_type
            / '{check_name}'
        )
        pyproject_file = folder_path / 'pyproject.toml'

        if pyproject_file.is_file():
            old_content = new_content = pyproject_file.read_text()

            for pattern in ('requires-python = ">={}"', "Programming Language :: Python :: {}"):
                new_content = new_content.replace(pattern.format(old_version), pattern.format(new_version))

            if old_content != new_content:
                pyproject_file.write_text(new_content)
                tracker.success()

        if (folder_path / 'hatch.toml').is_file():
            update_hatch_file(app, folder_path, new_version, old_version, tracker)


def update_ddev_pyproject_file(app: Application, new_version: str, old_version: str, tracker: ValidationTracker):
    import tomlkit

    config_file = app.repo.path / 'ddev' / 'pyproject.toml'
    config = tomlkit.parse(config_file.read_text())
    changed = False
    new_version = f"py{new_version.replace('.', '')}"
    old_version = f"py{old_version.replace('.', '')}"

    if black_config := config.get('tool', {}).get('black', {}):
        target_version = black_config.get('target-version', [])

        for index, version in enumerate(target_version):
            if version == old_version:
                target_version[index] = new_version
                tracker.success()
                changed = True
                break

    if ruff_config := config.get('tool', {}).get('ruff', {}):
        if ruff_config.get('target-version') == old_version:
            ruff_config['target-version'] = new_version
            tracker.success()
            changed = True

    if changed:
        config_file.write_text(tomlkit.dumps(config))


def update_setup_file(target, new_version: str, old_version: str, tracker: ValidationTracker):
    setup_file = target.path / 'setup.py'

    if setup_file.is_file():
        content = setup_file.read_text()

        if f"Programming Language :: Python :: {old_version}" in content:
            content = content.replace(
                f"Programming Language :: Python :: {old_version}", f"Programming Language :: Python :: {new_version}"
            )

            setup_file.write_text(content)
            tracker.success()


def update_constants_file(app: Application, new_version: str, old_version: str, tracker: ValidationTracker):
    constant_file = app.repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'

    lines = constant_file.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith('PYTHON_VERSION = '):
            lines[i] = line.replace(old_version, new_version)
            break

    constant_file.write_text(''.join(lines))
    tracker.success()


def update_pyproject_file(target, new_version: str, old_version: str, tracker: ValidationTracker):
    import tomlkit

    config_file = target.path / 'pyproject.toml'
    config = tomlkit.parse(config_file.read_text())
    changed = False

    classifiers = config.get('project', {}).get('classifiers', [])
    for index, classifier in enumerate(classifiers):
        if classifier == f"Programming Language :: Python :: {old_version}":
            classifiers[index] = f"Programming Language :: Python :: {new_version}"
            changed = True
            tracker.success()
            break

    if changed:
        config_file.write_text(tomlkit.dumps(config))


def update_hatch_file(app: Application, target_path, new_version: str, old_version: str, tracker: ValidationTracker):
    import tomlkit

    config_file = target_path / 'hatch.toml'

    if not config_file.exists():
        return

    test_config = tomlkit.parse(config_file.read_text())
    changed = False

    for env in test_config.get('envs', {}).values():
        if update_hatch_env(app, env, new_version, old_version, config_file, tracker):
            changed = True

    if changed:
        config_file.write_text(tomlkit.dumps(test_config))


def update_hatch_env(
    app: Application, env, new_version: str, old_version: str, config_file, tracker: ValidationTracker
) -> bool:
    changed = False

    default_python = env.get('python', '')
    if default_python == old_version:
        env['python'] = new_version
        tracker.success()
        changed = True

    for variables in env.get('matrix', []):
        pythons = variables.get('python', [])
        for i, python in enumerate(pythons):
            if python == old_version:
                pythons[i] = new_version
                tracker.success()
                changed = True

    for overrides in env.get('overrides', {}).get('matrix', {}).get('python', {}).values():
        for override in overrides:
            pythons = override.get('if', [])
            for i, python in enumerate(pythons):
                if python == old_version:
                    pythons[i] = new_version
                    tracker.success()
                    changed = True

    if isinstance(env.get('overrides', {}), dict):
        for name in list(env.get('overrides', {}).get('name', {}).keys()):
            if f"py{old_version}" in name:
                # TODO I don't find a way to keep the exact same format when I modify this.
                app.display_warning(f'An override has been found in {config_file}. Please manually update it.')

    return changed
