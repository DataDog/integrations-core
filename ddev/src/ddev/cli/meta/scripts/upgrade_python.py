# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('upgrade-python', short_help='Upgrade the Python version throughout the repository')
@click.argument('version')
@click.pass_obj
def upgrade_python(app: Application, version: str):
    """Upgrade the Python version of all test environments.

    \b
    `$ ddev meta scripts upgrade-python 3.11`
    """
    import tomlkit

    from ddev.repo.constants import PYTHON_VERSION as old_version

    tracker = app.create_validation_tracker('Python upgrades')

    for target in app.repo.integrations.iter_testable(['all']):
        config_file = target.path / 'hatch.toml'
        test_config = tomlkit.parse(config_file.read_text())
        changed = False

        for env in test_config.get('envs', {}).values():
            default_python = env.get('python', '')
            if default_python == old_version:
                env['python'] = version
                tracker.success()
                changed = True

            for variables in env.get('matrix', []):
                pythons = variables.get('python', [])
                for i, python in enumerate(pythons):
                    if python == old_version:
                        pythons[i] = version
                        tracker.success()
                        changed = True

            for overrides in env.get('overrides', {}).get('matrix', {}).get('python', {}).values():
                for override in overrides:
                    pythons = override.get('if', [])
                    for i, python in enumerate(pythons):
                        if python == old_version:
                            pythons[i] = version
                            tracker.success()
                            changed = True

        if changed:
            config_file.write_text(tomlkit.dumps(test_config))

    if app.repo.name == 'core':
        constant_file = app.repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'

        lines = constant_file.read_text().splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith('PYTHON_VERSION = '):
                lines[i] = line.replace(old_version, version)
                break

        constant_file.write_text(''.join(lines))
        tracker.success()

    tracker.display()

    if tracker.errors:  # no cov
        app.abort()
