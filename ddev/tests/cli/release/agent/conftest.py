# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.repo.core import Repository


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
    repo.git.run('config', 'tag.gpgsign', 'false')

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
    write_agent_requirements(repo.path, ["datadog-checks-downloader==4.0.0"])
    commit('fifth')
    repo.git.run('tag', '7.41.0')

    # Satisfy manifest requirements
    write_dummy_manifest(repo.path, 'foo')
    write_dummy_manifest(repo.path, 'bar')
    write_dummy_manifest(repo.path, 'onlywin')
    write_dummy_pyproject(repo.path, 'datadog_checks_downloader')
    write_dummy_pyproject(repo.path, 'datadog_checks_base')

    yield repo


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


def write_dummy_pyproject(repo_path, integration):
    (repo_path / integration).mkdir(exist_ok=True)

    file = repo_path / integration / 'pyproject.toml'
    file.write_text(
        f"""[project]
name = "{integration}"
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: BSD License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.12",
]
    """
    )


@pytest.fixture
def repo_with_new_integration_patched(tmp_path_factory, config_file):
    """
    Sets up a repo where a new integration is released at version 1.0.1 (not 1.0.0).
    This simulates the case where a new integration is added and then patched
    before the final agent release (e.g., fixes made during RC cycle).
    """
    repo_path = tmp_path_factory.mktemp('integrations-core')
    repo = Repository('integrations-core', str(repo_path))

    def commit(msg):
        repo.git.run('commit', '--no-verify', '-a', '-m', msg)

    repo.git.run('init')
    repo.git.run('config', 'user.email', 'you@example.com')
    repo.git.run('config', 'user.name', 'Your Name')
    repo.git.run('config', 'commit.gpgsign', 'false')
    repo.git.run('config', 'tag.gpgsign', 'false')

    # Agent 7.49.0: existing integration only
    write_agent_requirements(repo.path, ['datadog-existingcheck==2.0.0'])
    repo.git.run('add', '.')
    commit('7.49.0 release')
    repo.git.run('tag', '7.49.0')

    # Agent 7.50.0-rc.1: new integration added at 1.0.0 (RC tag, should be ignored by changelog)
    write_agent_requirements(repo.path, ['datadog-existingcheck==2.0.0', 'datadog-newcheck==1.0.0'])
    commit('7.50.0-rc.1 release')
    repo.git.run('tag', '7.50.0-rc.1')

    # Agent 7.50.0-rc.2: newcheck patched to 1.0.1 (RC tag, should be ignored by changelog)
    write_agent_requirements(repo.path, ['datadog-existingcheck==2.0.0', 'datadog-newcheck==1.0.1'])
    commit('7.50.0-rc.2 release')
    repo.git.run('tag', '7.50.0-rc.2')

    # Agent 7.50.0: final release with newcheck at 1.0.1 (same content as rc.2)
    # The changelog should compare this against 7.49.0 (not the RCs) and detect newcheck as NEW
    repo.git.run('tag', '7.50.0')

    write_dummy_manifest(repo.path, 'existingcheck')
    write_dummy_manifest(repo.path, 'newcheck')

    config_file.model.repos['core'] = str(repo.path)
    config_file.save()

    yield repo, None
