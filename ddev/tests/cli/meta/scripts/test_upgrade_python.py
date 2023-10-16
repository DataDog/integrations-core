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
    assert result.output == 'Python upgrades\n\nPassed: 2\n'

    contents = constant_file.read_text()
    assert f'PYTHON_VERSION = {old_version!r}' not in contents
    assert f'PYTHON_VERSION = {new_version!r}' in contents

    hatch_file = fake_repo.path / 'dummy' / 'hatch.toml'
    contents = hatch_file.read_text()
    assert f'python = ["2.7", "{old_version}"]' not in contents
    assert f'python = ["2.7", "{new_version}"]' in contents
