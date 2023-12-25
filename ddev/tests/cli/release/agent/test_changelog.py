# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pytest


def test_changelog_without_arguments(fake_changelog, ddev):
    result = ddev('release', 'agent', 'changelog')

    assert result.exit_code == 0
    assert result.output.rstrip('\n') == fake_changelog


def test_changelog_write_without_force_aborts_when_changelog_already_exists(
    repo_with_fake_changelog,
    fake_changelog,
    ddev,
    mocker,
):
    repo, fake_changelog = repo_with_fake_changelog

    # Create the changelog to trigger the condition
    open(repo.path / 'AGENT_CHANGELOG.md', 'w').close()
    mock_fetch_tags = mocker.patch('ddev.utils.git.GitManager.fetch_tags')

    result = ddev('release', 'agent', 'changelog', '--write')
    assert result.exit_code == 1
    assert re.match(
        'Output file (.*?)AGENT_CHANGELOG.md already exists, run the command again with --force to overwrite',
        result.output,
    )

    assert mock_fetch_tags.call_count == 1


def test_changelog_write_force(repo_with_fake_changelog, fake_changelog, ddev, mocker):
    repo, fake_changelog = repo_with_fake_changelog
    mock_fetch_tags = mocker.patch('ddev.utils.git.GitManager.fetch_tags')

    result = ddev('release', 'agent', 'changelog', '--write', '--force')
    assert result.exit_code == 0
    with open(repo.path / 'AGENT_CHANGELOG.md') as f:
        assert f.read().rstrip('\n') == fake_changelog

    assert mock_fetch_tags.call_count == 1


def test_changelog_since_to(fake_changelog, ddev, mocker):
    mock_fetch_tags = mocker.patch('ddev.utils.git.GitManager.fetch_tags')

    result = ddev('release', 'agent', 'changelog', '--since', '7.38.0', '--to', '7.39.0')
    assert result.exit_code == 0

    expected_output = (
        """## Datadog Agent version [7.39.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7390)

* bar [2.0.0](https://github.com/DataDog/integrations-core/blob/master/bar/CHANGELOG.md) **BREAKING CHANGE**
"""
        "* datadog_checks_base [3.0.0]"
        "(https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/CHANGELOG.md) "
        "**BREAKING CHANGE**"
    )
    assert result.output.rstrip('\n') == expected_output.strip('\n')
    assert mock_fetch_tags.call_count == 1


@pytest.fixture
def repo_with_fake_changelog(repo_with_history, config_file):
    config_file.model.repos['core'] = str(repo_with_history.path)
    config_file.save()
    # ruff: noqa: E501
    expected_output = (
        """
## Datadog Agent version [7.41.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7410)

* datadog_checks_downloader [4.0.0](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_downloader/CHANGELOG.md)

## Datadog Agent version [7.40.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7400)

* onlywin [1.0.0](https://github.com/DataDog/integrations-core/blob/master/onlywin/CHANGELOG.md)

## Datadog Agent version [7.39.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7390)

* bar [2.0.0](https://github.com/DataDog/integrations-core/blob/master/bar/CHANGELOG.md) **BREAKING CHANGE**
"""
        "* datadog_checks_base [3.0.0]"
        "(https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/CHANGELOG.md) "
        "**BREAKING CHANGE**"
        """

## Datadog Agent version [7.38.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7380)

* foo [1.5.0](https://github.com/DataDog/integrations-core/blob/master/foo/CHANGELOG.md)
* bar [1.0.0](https://github.com/DataDog/integrations-core/blob/master/bar/CHANGELOG.md)
* datadog_checks_base [2.1.3](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/CHANGELOG.md)
"""
    )
    return (
        repo_with_history,
        expected_output.strip('\n'),
    )


@pytest.fixture
def fake_changelog(repo_with_fake_changelog):
    _, fake_changelog = repo_with_fake_changelog
    return fake_changelog
