# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .conftest import NEW_PYTHON_VERSION, OLD_PYTHON_VERSION


def test_update_py_config(fake_repo, ddev):
    constant_file = fake_repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
    contents = constant_file.read_text()

    assert f'PYTHON_VERSION = {OLD_PYTHON_VERSION!r}' in contents
    assert f'PYTHON_VERSION = {NEW_PYTHON_VERSION!r}' not in contents

    result = ddev('meta', 'scripts', 'update-python-config', NEW_PYTHON_VERSION)

    assert result.exit_code == 0, result.output
    assert result.output.endswith('Python upgrades\n\nPassed: 9\n')

    contents = constant_file.read_text()
    assert f'PYTHON_VERSION = {OLD_PYTHON_VERSION!r}' not in contents
    assert f'PYTHON_VERSION = {NEW_PYTHON_VERSION!r}' in contents

    ci_file = fake_repo.path / '.github' / 'workflows' / 'build-ddev.yml'
    contents = ci_file.read_text()
    assert f'PYTHON_VERSION: "{OLD_PYTHON_VERSION}"' not in contents
    assert f'PYTHON_VERSION: "{NEW_PYTHON_VERSION}"' in contents

    yaml_workflow = fake_repo.path / '.github' / 'workflows' / 'claim-pypi-name.yaml'
    contents = yaml_workflow.read_text()
    assert f'python-version: "{OLD_PYTHON_VERSION}"' not in contents
    assert f'python-version: "{NEW_PYTHON_VERSION}"' in contents

    hatch_file = fake_repo.path / 'dummy' / 'hatch.toml'
    contents = hatch_file.read_text()
    assert f'python = ["{OLD_PYTHON_VERSION}"]' not in contents
    assert f'python = ["{NEW_PYTHON_VERSION}"]' in contents

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

    # Explicit content assertions on the rewritten ddev/pyproject.toml: this
    # captures the actual contract `update_ddev_pyproject_file` upholds today
    # (no `[tool.black]` block survives, and `[tool.ruff].target-version` is
    # the only target-version key bumped). Counter-only assertions above can
    # mask regressions where some unrelated tracker increment compensates for
    # a missed rewrite.
    ddev_pyproject = fake_repo.path / 'ddev' / 'pyproject.toml'
    new_target_token = f"py{NEW_PYTHON_VERSION.replace('.', '')}"
    old_target_token = f"py{OLD_PYTHON_VERSION.replace('.', '')}"
    contents = ddev_pyproject.read_text()
    assert '[tool.black]' not in contents
    assert f'target-version = "{new_target_token}"' in contents
    assert f'target-version = "{old_target_token}"' not in contents
