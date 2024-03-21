# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import yaml


@pytest.mark.parametrize('repo_fixture', ['fake_extras_repo', 'fake_marketplace_repo'])
def test_labeler_config_not_integrations_core(repo_fixture, ddev, config_file, request):
    fixture = request.getfixturevalue(repo_fixture)
    os.remove(fixture.path / '.github' / 'workflows' / 'config' / 'labeler.yml')
    result = ddev('validate', 'labeler')
    assert result.exit_code == 0, result.output


def test_labeler_config_does_not_exist(fake_repo, ddev):
    os.remove(fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml')
    result = ddev('validate', 'labeler')

    assert result.exit_code == 1, result.output
    assert "Unable to find the PR Labels config file" in result.output


def test_labeler_unknown_integration_in_config_file(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        labeler_test_config(["dummy", "dummy2", 'dummy3'])
    )

    result = ddev('validate', 'labeler')

    assert result.exit_code == 1, result.output
    assert "Unknown check label `integration/dummy3` found in PR labels config" in result.output


def test_labeler_integration_not_in_config_file(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(labeler_test_config(["dummy"]))

    result = ddev('validate', 'labeler')

    assert result.exit_code == 1, result.output
    assert "Check `dummy2` does not have an integration PR label" in result.output


def test_labeler_invalid_configuration(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        """changelog/no-changelog:
- any:
  - requirements-agent-release.txt
  - '*/__about__.py'
- all:
  - '!*/datadog_checks/**'
  - '!*/pyproject.toml'
  - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- datadog_checks_tests_helper/**/*
integration/dummy:
- dummy/**/*
integration/dummy2:
- something
release:
- '*/__about__.py'
    """,
    )

    result = ddev('validate', 'labeler')

    assert result.exit_code == 1, result.output
    assert (
        "Integration PR label `integration/dummy2` is not properly configured: \n    `['something']`" in result.output
    )


def test_labeler_valid_configuration(fake_repo, ddev):
    result = ddev('validate', 'labeler')

    assert result.exit_code == 0, result.output
    assert "Labeler configuration is valid" in result.output


def test_labeler_sync_remove_integration_in_config(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        labeler_test_config(["dummy", "dummy2", "dummy3"])
    )

    result = ddev('validate', 'labeler', '--sync')

    assert result.exit_code == 0, result.output
    assert 'Removing `integration/dummy3` only found in labeler config' in result.output
    assert 'Labeler configuration is valid' in result.output
    assert 'Successfully fixed' in result.output

    assert (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text() == labeler_test_config(
        ["dummy", "dummy2"]
    )


def test_labeler_sync_add_integration_in_config(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(labeler_test_config(["dummy"]))

    result = ddev('validate', 'labeler', '--sync')

    assert result.exit_code == 0, result.output
    assert 'Adding config for `dummy2`' in result.output
    assert 'Labeler configuration is valid' in result.output
    assert 'Successfully fixed' in result.output

    assert (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text() == labeler_test_config(
        ["dummy", "dummy2"]
    )


def test_labeler_fix_existing_integration_in_config(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        """changelog/no-changelog:
- any:
  - requirements-agent-release.txt
  - '*/__about__.py'
- all:
  - '!*/datadog_checks/**'
  - '!*/pyproject.toml'
  - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- datadog_checks_tests_helper/**/*
integration/dummy:
- dummy/**/*
integration/dummy2:
- something
release:
- '*/__about__.py'
    """,
    )

    result = ddev('validate', 'labeler', '--sync')

    assert result.exit_code == 0, result.output
    assert 'Fixing label config for `dummy2`' in result.output
    assert 'Labeler configuration is valid' in result.output
    assert 'Successfully fixed' in result.output
    assert (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text() == labeler_test_config(
        ["dummy", "dummy2"]
    )


def labeler_test_config(integrations):
    config = yaml.safe_load(
        """
changelog/no-changelog:
- any:
  - requirements-agent-release.txt
  - '*/__about__.py'
- all:
  - '!*/datadog_checks/**'
  - '!*/pyproject.toml'
  - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- datadog_checks_tests_helper/**/*
release:
- '*/__about__.py'
"""
    )

    for integration in integrations:
        config[f"integration/{integration}"] = [f"{integration}/**/*"]

    return yaml.dump(config, default_flow_style=False, sort_keys=True)
