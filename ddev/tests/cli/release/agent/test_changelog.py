# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from contextlib import contextmanager

import pytest
from datadog_checks.dev.tooling.constants import get_root, set_root
from ddev.repo.core import Repository


def test_changelog_without_arguments(fake_changelog, ddev):

    result = ddev('release', 'agent', 'changelog')

    assert result.exit_code == 0
    assert result.output.rstrip('\n') == fake_changelog


def test_changelog_write_without_force_aborts(fake_changelog, ddev):
    # Note, this test has the implicit assumption coming from the `repository` fixture
    # that the changelog file 'AGENT_CHANGELOG.md' already exists, and that's why it must fail.
    result = ddev('release', 'agent', 'changelog', '--write')
    assert result.exit_code == 1
    assert re.match(
        'Output file (.*?)AGENT_CHANGELOG.md already exists, run the command again with --force to overwrite',
        result.output,
    )


def test_changelog_write_force(repository, fake_changelog, ddev):
    result = ddev('release', 'agent', 'changelog', '--write', '--force')
    assert result.exit_code == 0
    with open(repository.path / 'AGENT_CHANGELOG.md') as f:
        assert f.read().rstrip('\n') == fake_changelog


def test_changelog_since_to(repository, fake_changelog, ddev):
    result = ddev('release', 'agent', 'changelog', '--since', '7.38.0', '--to', '7.39.0')
    assert result.exit_code == 0
    assert (
        result.output.rstrip('\n')
        == """
## Datadog Agent version [7.39.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7390)

* bar [2.0.0](https://github.com/DataDog/integrations-core/blob/master/bar/CHANGELOG.md) **BREAKING CHANGE**
""".strip(
            '\n'
        )
    )


@pytest.fixture
def fake_changelog(repository):
    """Sets up a repo with a fake sequence of agent releases, yielding the expected changelog."""

    repo = Repository(repository.path.name, str(repository.path))
    # Initial version with a single integration
    write_agent_requirements(repo.path, ['datadog-foo==1.0.0'])
    repo.git.run('commit', '-a', '-m', 'first')
    repo.git.run('tag', '7.37.0')
    # An update and a new integration
    write_agent_requirements(repo.path, ['datadog-foo==1.5.0', 'datadog-bar==1.0.0'])
    repo.git.run('commit', '-a', '-m', 'second')
    repo.git.run('tag', '7.38.0')
    # A breaking update
    write_agent_requirements(repo.path, ['datadog-bar==2.0.0'])
    repo.git.run('commit', '-a', '-m', 'third')
    repo.git.run('tag', '7.39.0')
    # An update with an environment marker
    write_agent_requirements(repo.path, ["datadog-onlywin==1.0.0; sys_platform == 'win32'"])
    repo.git.run('commit', '-a', '-m', 'fourth')
    repo.git.run('tag', '7.40.0')

    # Satisfy manifest requirements
    write_dummy_manifest(repo.path, 'foo')
    write_dummy_manifest(repo.path, 'bar')
    write_dummy_manifest(repo.path, 'onlywin')

    with temporary_root(repository.path):
        yield """
## Datadog Agent version [7.40.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7400)

* onlywin [1.0.0](https://github.com/DataDog/integrations-core/blob/master/onlywin/CHANGELOG.md)

## Datadog Agent version [7.39.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7390)

* bar [2.0.0](https://github.com/DataDog/integrations-core/blob/master/bar/CHANGELOG.md) **BREAKING CHANGE**

## Datadog Agent version [7.38.0](https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#7380)

* foo [1.5.0](https://github.com/DataDog/integrations-core/blob/master/foo/CHANGELOG.md)
* bar [1.0.0](https://github.com/DataDog/integrations-core/blob/master/bar/CHANGELOG.md)
""".strip(
            '\n'
        )


@contextmanager
def temporary_root(root):
    """A temporary way to set the root while migrating the command to get the root
    through ddev's config. Not thread-safe.
    """
    old_root = get_root()
    set_root(root)
    yield
    set_root(old_root)


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
