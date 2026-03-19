# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

import pytest


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
- changed-files:
  - any-glob-to-any-file:
    - requirements-agent-release.txt
    - '*/__about__.py'
- all:
  - changed-files:
    - any-glob-to-any-file:
      - '!*/datadog_checks/**'
      - '!*/pyproject.toml'
      - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- changed-files:
  - any-glob-to-any-file:
    - datadog_checks_tests_helper/**/*
integration/dummy:
- changed-files:
  - any-glob-to-any-file:
    - dummy/**/*
integration/dummy2:
- something
release:
- changed-files:
  - any-glob-to-any-file:
    - '*/__about__.py'
    """,
    )

    result = ddev('validate', 'labeler')

    assert result.exit_code == 1, result.output
    assert "Integration PR label `integration/dummy2` is not properly configured:" in result.output


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
    assert 'Successfully updated' in result.output

    assert (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text() == labeler_test_config(
        ["dummy", "dummy2"]
    )


def test_labeler_sync_add_integration_in_config(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(labeler_test_config(["dummy"]))

    result = ddev('validate', 'labeler', '--sync')

    assert result.exit_code == 0, result.output
    assert 'Adding config for `dummy2`' in result.output
    assert 'Labeler configuration is valid' in result.output
    assert 'Successfully updated' in result.output

    assert (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text() == labeler_test_config(
        ["dummy", "dummy2"]
    )


def test_labeler_fix_existing_integration_in_config(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        """\
changelog/no-changelog:
- changed-files:
  - any-glob-to-any-file:
    - requirements-agent-release.txt
    - '*/__about__.py'
- all:
  - changed-files:
    - any-glob-to-any-file:
      - '!*/datadog_checks/**'
      - '!*/pyproject.toml'
      - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- changed-files:
  - any-glob-to-any-file:
    - datadog_checks_tests_helper/**/*
integration/dummy:
- changed-files:
  - any-glob-to-any-file:
    - dummy/**/*
integration/dummy2:
- something
release:
- changed-files:
  - any-glob-to-any-file:
    - '*/__about__.py'
""",
    )

    result = ddev('validate', 'labeler', '--sync')

    assert result.exit_code == 0, result.output
    assert 'Fixing label config for `dummy2`' in result.output
    assert 'Labeler configuration is valid' in result.output
    assert 'Successfully updated' in result.output
    assert (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text() == labeler_test_config(
        ["dummy", "dummy2"]
    )


LONG_CHECK_NAME = "a_very_long_integration_name_that_exceeds_the_limit"


def test_labeler_sync_long_label_prompts_user_for_shorter_tag(fake_repo, ddev):
    long_check_dir = fake_repo.path / LONG_CHECK_NAME
    long_check_dir.mkdir()
    (long_check_dir / 'manifest.json').write_text('{}')

    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        labeler_test_config(["dummy", "dummy2"])
    )

    result = ddev('validate', 'labeler', '--sync', input='long_check\n')

    assert result.exit_code == 0, result.output
    assert 'exceeds the 50 character limit' in result.output
    assert f'Adding config for `{LONG_CHECK_NAME}`' in result.output
    assert 'Successfully updated' in result.output

    labeler_content = (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text()
    assert 'integration/long_check' in labeler_content
    assert f'{LONG_CHECK_NAME}/**/*' in labeler_content


def test_labeler_sync_long_label_user_provides_tag_with_prefix(fake_repo, ddev):
    long_check_dir = fake_repo.path / LONG_CHECK_NAME
    long_check_dir.mkdir()
    (long_check_dir / 'manifest.json').write_text('{}')

    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        labeler_test_config(["dummy", "dummy2"])
    )

    result = ddev('validate', 'labeler', '--sync', input='integration/long_check\n')

    assert result.exit_code == 0, result.output
    assert f'Adding config for `{LONG_CHECK_NAME}`' in result.output

    labeler_content = (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text()
    assert 'integration/long_check' in labeler_content
    assert 'integration/integration/' not in labeler_content


def test_labeler_sync_does_not_overwrite_custom_label(fake_repo, ddev):
    """When integration/dummy is a custom label pointing to dummy2's directory,
    --sync must not overwrite it when adding a label for the dummy integration."""
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        """\
changelog/no-changelog:
- changed-files:
  - any-glob-to-any-file:
    - requirements-agent-release.txt
    - '*/__about__.py'
- all:
  - changed-files:
    - any-glob-to-any-file:
      - '!*/datadog_checks/**'
      - '!*/pyproject.toml'
      - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- changed-files:
  - any-glob-to-any-file:
    - datadog_checks_tests_helper/**/*
integration/dummy:
- changed-files:
  - any-glob-to-any-file:
    - dummy2/**/*
release:
- changed-files:
  - any-glob-to-any-file:
    - '*/__about__.py'
""",
    )

    result = ddev('validate', 'labeler', '--sync')

    assert result.exit_code == 0, result.output
    assert 'Cannot auto-add label `integration/dummy` for `dummy`' in result.output
    assert 'already used for directory `dummy2`' in result.output

    labeler_content = (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text()
    assert 'dummy2/**/*' in labeler_content


def test_labeler_no_sync_label_conflict_reports_detailed_error(fake_repo, ddev):
    """When integration/dummy is a custom label pointing to dummy2's directory,
    validation without --sync should report that the label is already in use."""
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        """\
changelog/no-changelog:
- changed-files:
  - any-glob-to-any-file:
    - requirements-agent-release.txt
    - '*/__about__.py'
- all:
  - changed-files:
    - any-glob-to-any-file:
      - '!*/datadog_checks/**'
      - '!*/pyproject.toml'
      - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- changed-files:
  - any-glob-to-any-file:
    - datadog_checks_tests_helper/**/*
integration/dummy:
- changed-files:
  - any-glob-to-any-file:
    - dummy2/**/*
release:
- changed-files:
  - any-glob-to-any-file:
    - '*/__about__.py'
""",
    )

    result = ddev('validate', 'labeler')

    assert result.exit_code == 1, result.output
    assert 'does not have an integration PR label' in result.output
    assert 'already used for directory `dummy2`' in result.output


def test_labeler_sync_long_label_replacement_still_too_long(fake_repo, ddev):
    long_check_dir = fake_repo.path / LONG_CHECK_NAME
    long_check_dir.mkdir()
    (long_check_dir / 'manifest.json').write_text('{}')

    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        labeler_test_config(["dummy", "dummy2"])
    )

    still_too_long = "this_replacement_tag_is_also_way_too_long_for_limit"
    result = ddev('validate', 'labeler', '--sync', input=f'{still_too_long}\n')

    assert result.exit_code == 1, result.output
    assert 'still too long' in result.output


def test_labeler_duplicate_yaml_key_reports_error(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        """\
changelog/no-changelog:
- changed-files:
  - any-glob-to-any-file:
    - requirements-agent-release.txt
    - '*/__about__.py'
- all:
  - changed-files:
    - any-glob-to-any-file:
      - '!*/datadog_checks/**'
      - '!*/pyproject.toml'
      - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- changed-files:
  - any-glob-to-any-file:
    - datadog_checks_tests_helper/**/*
integration/dummy:
- changed-files:
  - any-glob-to-any-file:
    - dummy/stale/**/*
integration/dummy2:
- changed-files:
  - any-glob-to-any-file:
    - dummy2/**/*
integration/dummy:
- changed-files:
  - any-glob-to-any-file:
    - dummy/**/*
release:
- changed-files:
  - any-glob-to-any-file:
    - '*/__about__.py'
""",
    )

    result = ddev('validate', 'labeler')

    assert result.exit_code == 1, result.output
    output = re.sub(r"\s+", " ", result.output)
    assert 'Duplicate key `integration/dummy`' in output
    assert 'running `--sync` will keep the last occurrence' in output


def test_labeler_sync_removes_duplicate_yaml_key(fake_repo, ddev):
    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        """\
changelog/no-changelog:
- changed-files:
  - any-glob-to-any-file:
    - requirements-agent-release.txt
    - '*/__about__.py'
- all:
  - changed-files:
    - any-glob-to-any-file:
      - '!*/datadog_checks/**'
      - '!*/pyproject.toml'
      - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- changed-files:
  - any-glob-to-any-file:
    - datadog_checks_tests_helper/**/*
integration/dummy:
- changed-files:
  - any-glob-to-any-file:
    - dummy/stale/**/*
integration/dummy2:
- changed-files:
  - any-glob-to-any-file:
    - dummy2/**/*
integration/dummy:
- changed-files:
  - any-glob-to-any-file:
    - dummy/**/*
release:
- changed-files:
  - any-glob-to-any-file:
    - '*/__about__.py'
""",
    )

    result = ddev('validate', 'labeler', '--sync')

    assert result.exit_code == 0, result.output
    output = re.sub(r"\s+", " ", result.output)
    assert (
        'Removing duplicate key `integration/dummy` from labeler config. Only the last occurrence will be kept.'
        in output
    )
    assert 'Successfully updated' in output

    labeler_content = (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').read_text()
    assert labeler_content.count('integration/dummy:') == 1
    assert 'dummy/**/*' in labeler_content
    assert 'dummy/stale/**/*' not in labeler_content


def test_labeler_no_sync_long_label_reports_error(fake_repo, ddev):
    long_check_dir = fake_repo.path / LONG_CHECK_NAME
    long_check_dir.mkdir()
    (long_check_dir / 'manifest.json').write_text('{}')

    (fake_repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml').write_text(
        labeler_test_config(["dummy", "dummy2"])
    )

    result = ddev('validate', 'labeler')

    assert result.exit_code == 1, result.output
    output = re.sub(r"\s+", " ", result.output)
    assert "does not have an integration PR label" in output


def labeler_test_config(integrations):
    config = """\
changelog/no-changelog:
- changed-files:
  - any-glob-to-any-file:
    - requirements-agent-release.txt
    - '*/__about__.py'
- all:
  - changed-files:
    - any-glob-to-any-file:
      - '!*/datadog_checks/**'
      - '!*/pyproject.toml'
      - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- changed-files:
  - any-glob-to-any-file:
    - datadog_checks_tests_helper/**/*
"""

    for integration in integrations:
        config += f"""\
integration/{integration}:
- changed-files:
  - any-glob-to-any-file:
    - {integration}/**/*
"""
    config += """\
release:
- changed-files:
  - any-glob-to-any-file:
    - '*/__about__.py'
"""

    return config
