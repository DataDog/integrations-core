# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict

from ddev.repo.constants import PYTHON_VERSION


def test_upgrade_python(ddev, repository):
    major, minor = PYTHON_VERSION.split('.')
    new_version = f'{major}.{int(minor) + 1}'

    changes = defaultdict(list)
    for entry in repository.path.iterdir():
        config_file = entry / 'hatch.toml'
        if not config_file.is_file():
            continue

        for i, line in enumerate(config_file.read_text().splitlines()):
            if line.startswith('python = [') and PYTHON_VERSION in line:
                changes[config_file].append(i)

    minimum_changes = sum(map(len, changes.values()))

    constant_file = repository.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
    contents = constant_file.read_text()

    assert f'PYTHON_VERSION = {PYTHON_VERSION!r}' in contents
    assert f'PYTHON_VERSION = {new_version!r}' not in contents

    result = ddev('meta', 'scripts', 'upgrade-python', new_version)

    assert result.exit_code == 0, result.output
    assert result.output.startswith('Python upgrades\n\nPassed: ')

    passed = int(result.output.partition('Passed:')[2].strip())
    assert passed >= minimum_changes

    contents = constant_file.read_text()
    assert f'PYTHON_VERSION = {PYTHON_VERSION!r}' not in contents
    assert f'PYTHON_VERSION = {new_version!r}' in contents
