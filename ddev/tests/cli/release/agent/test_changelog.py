# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pytest

from ddev.repo.core import Repository


def test_changelog_without_arguments(fake_changelog, ddev):
    result = ddev('release', 'agent', 'changelog')

    assert result.exit_code == 0
    assert result.output.rstrip('\n') == fake_changelog


def test_changelog_write_without_force_aborts_when_changelog_already_exists(
    repo_with_fake_changelog, fake_changelog, ddev
):
    repo, fake_changelog = repo_with_fake_changelog

    # Create the changelog to trigger the condition
    open(repo.path / 'AGENT_CHANGELOG.md', 'w').close()

    result = ddev('release', 'agent', 'changelog', '--write')
    assert result.exit_code == 1
    assert re.match(
        'Output file (.*?)AGENT_CHANGELOG.md already exists, run the command again with --force to overwrite',
        result.output,
    )


def test_changelog_write_force(repo_with_fake_changelog, fake_changelog, ddev):
    repo, fake_changelog = repo_with_fake_changelog

    result = ddev('release', 'agent', 'changelog', '--write', '--force')
    assert result.exit_code == 0
    with open(repo.path / 'AGENT_CHANGELOG.md') as f:
        assert f.read().rstrip('\n') == fake_changelog


def test_changelog_since_to(fake_changelog, ddev):
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


@pytest.fixture
def repo_with_history(tmp_path_factory):
    """Sets up a repo with a fake sequence of agent releases, yielding the expected changelog."""
    # Initialize a new repo
    repo_path = tmp_path_factory.mktemp('integrations-core')
    repo = Repository('integrations-core', str(repo_path))

    def commit(msg):
        # Using `--no-verify` avoids commit hooks that can slow down the tests and are not necessary
        repo.git.run('commit', '--no-verify', '-a', '-m', msg)

    repo.git.run('init')
    repo.git.run('config', 'user.email', 'you@example.com')
    repo.git.run('config', 'user.name', 'Your Name')
    repo.git.run('config', 'commit.gpgsign', 'false')

    # Initial version with a single integration
    write_agent_requirements(repo.path, ['datadog-foo==1.0.0'])
    repo.git.run('add', '.')
    commit('first')
    repo.git.run('tag', '7.37.0')
    # An update and a new integration, using folder names instead of package names, as has erroneously
    # been the case at some point in our git history. We want to test that we're resilient to that.
    write_agent_requirements(repo.path, ['foo==1.5.0', 'bar==1.0.0', 'datadog_checks_base==2.1.3'])
    commit('second')
    repo.git.run('tag', '7.38.0')
    # Breaking updates
    write_agent_requirements(repo.path, ['datadog-bar==2.0.0', 'datadog-checks-base==3.0.0'])
    commit('third')
    repo.git.run('tag', '7.39.0')
    # An update with an environment marker
    write_agent_requirements(repo.path, ["datadog-onlywin==1.0.0; sys_platform == 'win32'"])
    commit('fourth')
    repo.git.run('tag', '7.40.0')

    # Satisfy manifest requirements
    write_dummy_manifest(repo.path, 'foo')
    write_dummy_manifest(repo.path, 'bar')
    write_dummy_manifest(repo.path, 'onlywin')
    write_dummy_manifest(repo.path, 'datadog_checks_base')

    yield repo


@pytest.fixture
def repo_with_fake_changelog(repo_with_history, config_file):
    config_file.model.repos['core'] = str(repo_with_history.path)
    config_file.save()
    expected_output = (
        """
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


def write_agent_requirements(repo_path, requirements):
    with open(repo_path / 'requirements-agent-release.txt', 'w') as req_file:
        req_file.write('\n'.join(requirements))


def write_dummy_manifest(repo_path, integration):
    """Write a manifest to satisfy the initial requirement of having to go through `Manifest.load_manifest()`."""
    (repo_path / integration).mkdir(exist_ok=True)
    import json

    with open(repo_path / integration / 'manifest.json', 'w') as f:
        json.dump(
            {
                'manifest_version': '2.0.0',
                'assets': {'integration': {'source_type_name': integration}},
            },
            f,
        )
