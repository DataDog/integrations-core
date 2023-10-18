# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def test_upgrade_python(fake_repo, ddev):
    new_version = "3.11"
    old_version = "3.9"

    constant_file = fake_repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
    contents = constant_file.read_text()

    assert f'PYTHON_VERSION = {old_version!r}' in contents
    assert f'PYTHON_VERSION = {new_version!r}' not in contents

    result = ddev('meta', 'scripts', 'upgrade-python', new_version)

    assert result.exit_code == 0, result.output
    assert result.output.endswith('Python upgrades\n\nPassed: 7\n')

    contents = constant_file.read_text()
    assert f'PYTHON_VERSION = {old_version!r}' not in contents
    assert f'PYTHON_VERSION = {new_version!r}' in contents

    ci_file = fake_repo.path / '.github' / 'workflows' / 'build-ddev.yml'
    contents = ci_file.read_text()
    assert f'PYTHON_VERSION: "{old_version}"' not in contents
    assert f'PYTHON_VERSION: "{new_version}"' in contents

    hatch_file = fake_repo.path / 'dummy' / 'hatch.toml'
    contents = hatch_file.read_text()
    assert f'python = ["2.7", "{old_version}"]' not in contents
    assert f'python = ["2.7", "{new_version}"]' in contents

    pyproject_file = fake_repo.path / 'dummy' / 'pyproject.toml'
    contents = pyproject_file.read_text()
    assert f'Programming Language :: Python :: {old_version}' not in contents
    assert f'Programming Language :: Python :: {new_version}' in contents

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
    assert f'Programming Language :: Python :: {old_version}' not in contents
    assert f'Programming Language :: Python :: {new_version}' in contents
