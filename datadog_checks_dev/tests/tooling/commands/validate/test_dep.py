# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import tomli_w
from click.testing import CliRunner

from datadog_checks.dev.tooling.commands.validate.dep import dep
from datadog_checks.dev.tooling.utils import set_root


def test_invalid_third_party_integration(fake_repo):
    create_integration(fake_repo, 'foo', ['dep-a==1.0.0', 'dep-b==3.1.4'])

    runner = CliRunner()
    result = runner.invoke(dep)

    assert result.exit_code == 1
    assert "Third-party" in result.output
    assert "base check dependency" in result.output


def test_multiple_invalid_third_party_integrations(fake_repo):
    create_integration(fake_repo, 'foo11', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'foo22', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'foo33', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'foo44', ['datadog-checks-base>=37.21.0', 'dep-a==1.0.0'])

    runner = CliRunner()
    result = runner.invoke(dep)

    assert result.exit_code == 1
    assert "Third-party" in result.output
    assert "base check dependency" in result.output


def test_valid_integration(fake_repo):
    create_integration(fake_repo, 'foo55', ['datadog-checks-base>=37.21.0'])
    runner = CliRunner()
    result = runner.invoke(dep)

    assert result.exit_code == 0
    assert "valid" in result.output


def test_one_valid_one_invalid_integration(fake_repo):
    create_integration(fake_repo, 'foo66', ['dep-a==1.0.0', 'dep-b==3.1.4', 'datadog-checks-base>=37.21.0'])
    create_integration(fake_repo, 'foo67', ['datadog-checks-base>=37.21.0'])

    runner = CliRunner()
    result = runner.invoke(dep)

    assert result.exit_code == 1
    assert "Third-party" in result.output


def create_integration(root, name, dependencies):
    """Helper function to create a fake integration for testing."""
    integration_dir = root / name
    integration_dir.mkdir(exist_ok=True)
    with open(integration_dir / 'pyproject.toml', 'wb') as f:
        tomli_w.dump({'project': {'dependencies': dependencies}}, f)

    # Fill stuff needed for it to be recognized as an agent check
    (integration_dir / 'datadog_checks' / name).mkdir(parents=True)
    (integration_dir / 'datadog_checks' / name / '__about__.py').touch()
    (integration_dir / 'datadog_checks' / name / '__init__.py').write_text(
        """
import a
import b
"""
    )


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Create a minimal fake repo without config_file dependency."""
    data_folder = tmp_path / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data'
    data_folder.mkdir(parents=True)

    set_root(str(tmp_path))

    yield tmp_path

    set_root('')
