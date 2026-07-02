# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.release.changelog.show import _extract_version_section
from ddev.utils.fs import Path
from tests.helpers.git import ClonedRepo
from tests.helpers.runner import CliRunner

CHANGELOG_BODY = """\
# CHANGELOG - ddev

<!-- towncrier release notes start -->

## 16.1.1 / 2026-04-29

***Fixed***:

* Bumped datadog_checks_dev to version 38.0.0. Fixes dependency issues. ([#23516](https://github.com/DataDog/integrations-core/pull/23516))

## 16.1.0 / 2026-04-29

***Added***:

* Add async GitHub API client. ([#22734](https://github.com/DataDog/integrations-core/pull/22734))
* Use uv as the installer for hatch test environments. ([#23497](https://github.com/DataDog/integrations-core/pull/23497))

## 1.0.10 / 2024-01-01

***Fixed***:

* Older release that should not match against 1.0.1. ([#1](https://github.com/DataDog/integrations-core/pull/1))

## 1.0.1 / 2024-01-02

***Fixed***:

* Patch release. ([#2](https://github.com/DataDog/integrations-core/pull/2))
"""


@pytest.fixture
def ddev_changelog(repo_with_towncrier: ClonedRepo) -> Path:
    changelog = repo_with_towncrier.path / 'ddev' / 'CHANGELOG.md'
    changelog.write_text(CHANGELOG_BODY)
    return changelog


@pytest.mark.parametrize(
    'version, expected_substring, forbidden_substring',
    [
        pytest.param(
            '16.1.1',
            '* Bumped datadog_checks_dev to version 38.0.0',
            '## 16.1.0',
            id='middle_section',
        ),
        pytest.param(
            '16.1.0',
            '* Add async GitHub API client.',
            '## 16.1.1',
            id='multi_bullet_section',
        ),
        pytest.param(
            '1.0.1',
            '* Patch release.',
            '* Older release',
            id='strict_match_does_not_substring_into_1_0_10',
        ),
    ],
)
def test_extract_version_section_returns_expected_block(
    ddev_changelog: Path, version: str, expected_substring: str, forbidden_substring: str
):
    section = _extract_version_section(ddev_changelog, version)

    assert section is not None
    assert expected_substring in section
    assert forbidden_substring not in section
    assert not section.startswith('\n')
    assert not section.endswith('\n')


def test_extract_version_section_returns_none_for_missing_version(ddev_changelog: Path):
    assert _extract_version_section(ddev_changelog, '99.99.99') is None


def test_show_prints_section_to_stdout(ddev: CliRunner, ddev_changelog: Path, helpers):
    result = ddev('release', 'changelog', 'show', 'ddev', '16.1.1')

    assert result.exit_code == 0, result.output
    output = helpers.remove_trailing_spaces(result.output)
    assert 'Fixed:' in output
    assert 'Bumped datadog_checks_dev to version 38.0.0' in output
    assert '16.1.0' not in output


def test_show_writes_to_file(ddev: CliRunner, ddev_changelog: Path, tmp_path: Path):
    output_file = tmp_path / 'release-notes.md'

    result = ddev('release', 'changelog', 'show', 'ddev', '16.1.0', '--file', str(output_file))

    assert result.exit_code == 0, result.output
    assert f'Wrote changelog section for ddev 16.1.0 to {output_file}' in result.output
    contents = output_file.read_text()
    assert '* Add async GitHub API client.' in contents
    assert '## 16.1.1' not in contents


def test_show_creates_missing_parent_directories(ddev: CliRunner, ddev_changelog: Path, tmp_path: Path):
    output_file = tmp_path / 'nested' / 'sub' / 'release-notes.md'

    result = ddev('release', 'changelog', 'show', 'ddev', '16.1.1', '--file', str(output_file))

    assert result.exit_code == 0, result.output
    assert output_file.is_file()
    assert '* Bumped datadog_checks_dev to version 38.0.0' in output_file.read_text()


def test_show_strict_version_matching_against_substring(ddev: CliRunner, ddev_changelog: Path, helpers):
    result = ddev('release', 'changelog', 'show', 'ddev', '1.0.1')

    assert result.exit_code == 0, result.output
    output = helpers.remove_trailing_spaces(result.output)
    assert 'Patch release.' in output
    assert 'Older release' not in output


def test_show_aborts_when_version_missing(ddev: CliRunner, ddev_changelog: Path):
    result = ddev('release', 'changelog', 'show', 'ddev', '99.99.99')

    assert result.exit_code != 0
    assert 'No changelog section found for ddev version 99.99.99' in result.output


def test_show_aborts_when_changelog_missing(ddev: CliRunner, repo_with_towncrier: ClonedRepo):
    changelog = repo_with_towncrier.path / 'ddev' / 'CHANGELOG.md'
    if changelog.is_file():
        changelog.unlink()

    result = ddev('release', 'changelog', 'show', 'ddev', '1.0.0')

    assert result.exit_code != 0
    assert 'Changelog not found' in result.output


def test_show_aborts_for_unknown_target(ddev: CliRunner, repo_with_towncrier: ClonedRepo):
    result = ddev('release', 'changelog', 'show', 'definitely_not_an_integration', '1.0.0')

    assert result.exit_code != 0
    assert 'Unknown target: definitely_not_an_integration' in result.output


@pytest.mark.parametrize(
    'args, expected_message',
    [
        pytest.param([], "Missing argument 'TARGET'", id='no_args'),
        pytest.param(['ddev'], "Missing argument 'VERSION'", id='target_only'),
    ],
)
def test_show_argument_errors(ddev: CliRunner, repo_with_towncrier: ClonedRepo, args: list[str], expected_message: str):
    result = ddev('release', 'changelog', 'show', *args)

    assert result.exit_code != 0
    assert expected_message in result.output
