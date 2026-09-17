# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from types import SimpleNamespace

import pytest

from ddev.cli.release.agent.common import (
    UNRELEASED_INTEGRATIONS_CONFIG,
    agent_version_in_range,
    get_unreleased_integrations,
)


def test_integrations_without_arguments(fake_integrations, ddev):
    result = ddev('release', 'agent', 'integrations')

    assert result.exit_code == 0
    assert result.output.rstrip('\n') == fake_integrations


def test_integrations_write_without_force_aborts_when_changelog_already_exists(repo_with_fake_integrations, ddev):
    repo, fake_changelog = repo_with_fake_integrations

    # Create the integrations file to trigger the condition
    open(repo.path / 'AGENT_INTEGRATIONS.md', 'w').close()

    result = ddev('release', 'agent', 'integrations', '--write')
    assert result.exit_code == 1
    assert re.match(
        'Output file (.*?)AGENT_INTEGRATIONS.md already exists, run the command again with --force to overwrite',
        result.output,
    )


def test_integrations_write_force(repo_with_fake_integrations, ddev):
    repo, fake_changelog = repo_with_fake_integrations

    result = ddev('release', 'agent', 'integrations', '--write', '--force')
    assert result.exit_code == 0
    with open(repo.path / 'AGENT_INTEGRATIONS.md') as f:
        assert f.read().rstrip('\n') == fake_changelog


def test_integrations_since_to(fake_integrations, ddev):
    result = ddev('release', 'agent', 'integrations', '--since', '7.38.0', '--to', '7.39.0')
    assert result.exit_code == 0

    expected_output = """## Datadog Agent version 7.39.0

* datadog-bar: 2.0.0
* datadog-checks-base: 3.0.0

## Datadog Agent version 7.38.0

* foo: 1.5.0
* bar: 1.0.0
* datadog_checks_base: 2.1.3"""
    assert result.output.rstrip('\n') == expected_output.strip('\n')


@pytest.mark.parametrize(
    ('version', 'expected'),
    [
        pytest.param('7.74.0', True, id='lower-bound-inclusive'),
        pytest.param('7.78.0', True, id='upper-bound-inclusive'),
        pytest.param('7.77.0', True, id='middle'),
        pytest.param('7.73.0', False, id='below-range'),
        pytest.param('7.79.0', False, id='above-range'),
    ],
)
def test_agent_version_in_range_is_inclusive(version, expected):
    assert agent_version_in_range(version, '7.74.0..7.78.0') is expected


def test_agent_version_in_range_raises_on_malformed_range():
    with pytest.raises(ValueError, match="Invalid version range '7.74.0'"):
        agent_version_in_range('7.74.0', '7.74.0')


def test_get_unreleased_integrations_combines_both_keys():
    config_data = {
        'by-integration': {'datadog-bar': ['7.78.0']},
        'by-agent-version-range': {'7.74.0..7.78.0': ['datadog-foo']},
    }
    repo = SimpleNamespace(
        config=SimpleNamespace(
            get=lambda key, default=None: config_data if key == UNRELEASED_INTEGRATIONS_CONFIG else default,
        )
    )

    assert get_unreleased_integrations(repo, '7.78.0') == {'bar', 'foo'}


def test_integrations_skips_unreleased_integrations(repo_with_history, config_file, ddev, write_repo_config):
    config_file.model.repos['core'] = str(repo_with_history.path)
    config_file.save()
    write_repo_config(
        repo_with_history.path,
        """
[overrides.release.agent.unreleased-integrations.by-agent-version-range]
"7.38.0..7.39.0" = ["datadog-bar"]
""",
    )

    result = ddev('release', 'agent', 'integrations', '--since', '7.38.0', '--to', '7.38.0')
    assert result.exit_code == 0

    expected_output = """## Datadog Agent version 7.38.0

* foo: 1.5.0
* datadog_checks_base: 2.1.3"""
    assert result.output.rstrip('\n') == expected_output.strip('\n')


@pytest.fixture
def repo_with_fake_integrations(repo_with_history, config_file):
    config_file.model.repos['core'] = str(repo_with_history.path)
    config_file.save()
    expected_output = """
## Datadog Agent version 7.41.0

* datadog-checks-downloader: 4.0.0

## Datadog Agent version 7.40.0

* datadog-onlywin: 1.0.0

## Datadog Agent version 7.39.0

* datadog-bar: 2.0.0
* datadog-checks-base: 3.0.0

## Datadog Agent version 7.38.0

* foo: 1.5.0
* bar: 1.0.0
* datadog_checks_base: 2.1.3

## Datadog Agent version 7.37.0

* datadog-foo: 1.0.0
"""
    return (
        repo_with_history,
        expected_output.strip('\n'),
    )


@pytest.fixture
def fake_integrations(repo_with_fake_integrations):
    _, fake_integrations = repo_with_fake_integrations
    return fake_integrations
