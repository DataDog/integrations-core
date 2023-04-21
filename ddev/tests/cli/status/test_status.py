# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from ddev.config.constants import AppEnvVars
from ddev.utils.structures import EnvVars


def test_repo_configured_default(ddev, helpers, repository):
    result = ddev('status')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Repo: core @ {repository.path}
        Branch: {repository.testing_branch}
        Org: default
        """
    )


@pytest.mark.parametrize('repo_name', ['extras', 'marketplace'])
def test_repo_flags(ddev, helpers, repository, config_file, repo_name):
    config_file.model.repo = repo_name
    config_file.model.repos[config_file.model.repo.name] = str(repository.path)
    config_file.save()

    result = ddev(f'--{repo_name}', 'status')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Repo: {repo_name} @ {repository.path}
        Branch: {repository.testing_branch}
        Org: default
        """
    )


@pytest.mark.parametrize('repo_name', ['extras', 'marketplace'])
def test_repo_env_vars(ddev, helpers, repository, config_file, repo_name):
    config_file.model.repos[repo_name] = str(repository.path)
    config_file.save()

    with EnvVars({AppEnvVars.REPO: repo_name}):
        result = ddev('status')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Repo: {repo_name} @ {repository.path}
        Branch: {repository.testing_branch}
        Org: default
        """
    )


def test_org(ddev, helpers, repository, config_file):
    config_file.model.orgs['foo'] = {}
    config_file.model.org = 'foo'
    config_file.save()

    result = ddev('status')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Repo: core @ {repository.path}
        Branch: {repository.testing_branch}
        Org: foo
        """
    )


def test_changed_integrations(ddev, helpers, repository):
    new_integration = repository.path / 'new'
    new_integration.mkdir()
    (new_integration / 'manifest.json').touch()

    (repository.path / 'datadog_checks_base' / 'README.md').remove()

    result = ddev('status')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Repo: core @ {repository.path}
        Branch: {repository.testing_branch}
        Org: default
        Changed: datadog_checks_base, new
        """
    )
