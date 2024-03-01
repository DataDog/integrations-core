# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .conftest import NEW_PYTHON_VERSION, OLD_PYTHON_VERSION


def test_upgrade_python(fake_repo, ddev):
    constant_file = fake_repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
    contents = constant_file.read_text()

    assert f'PYTHON_VERSION = {OLD_PYTHON_VERSION!r}' in contents
    assert f'PYTHON_VERSION = {NEW_PYTHON_VERSION!r}' not in contents

    result = ddev('meta', 'scripts', 'upgrade-python', NEW_PYTHON_VERSION)

    assert result.exit_code == 0, result.output
    assert result.output.endswith('Python upgrades\n\nPassed: 9\n')

    contents = constant_file.read_text()
    assert f'PYTHON_VERSION = {OLD_PYTHON_VERSION!r}' not in contents
    assert f'PYTHON_VERSION = {NEW_PYTHON_VERSION!r}' in contents

    ci_file = fake_repo.path / '.github' / 'workflows' / 'build-ddev.yml'
    contents = ci_file.read_text()
    assert f'PYTHON_VERSION: "{OLD_PYTHON_VERSION}"' not in contents
    assert f'PYTHON_VERSION: "{NEW_PYTHON_VERSION}"' in contents

    hatch_file = fake_repo.path / 'dummy' / 'hatch.toml'
    contents = hatch_file.read_text()
    assert f'python = ["2.7", "{OLD_PYTHON_VERSION}"]' not in contents
    assert f'python = ["2.7", "{NEW_PYTHON_VERSION}"]' in contents

    for integration in ('dummy', 'datadog_checks_dependency_provider', 'logs_only'):
        pyproject_file = fake_repo.path / integration / 'pyproject.toml'
        contents = pyproject_file.read_text()
        assert f'Programming Language :: Python :: {OLD_PYTHON_VERSION}' not in contents
        assert f'Programming Language :: Python :: {NEW_PYTHON_VERSION}' in contents

    template_file = (
        fake_repo.path
        / 'datadog_checks_dev'
        / 'datadog_checks'
        / 'dev'
        / 'tooling'
        / 'templates'
        / 'integration'
        / 'check'
        / '{check_name}'
        / 'pyproject.toml'
    )
    contents = template_file.read_text()
    assert f'Programming Language :: Python :: {OLD_PYTHON_VERSION}' not in contents
    assert f'Programming Language :: Python :: {NEW_PYTHON_VERSION}' in contents
