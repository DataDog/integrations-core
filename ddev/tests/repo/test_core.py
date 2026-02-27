# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import cast

import pytest

from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig
from ddev.repo.constants import NOT_SHIPPABLE
from ddev.repo.core import IntegrationRegistry, Repository
from ddev.utils.fs import Path


def test_attributes(local_repo):
    repo = Repository(local_repo.name, str(local_repo))

    assert repo.name == local_repo.name
    assert repo.path == local_repo
    assert isinstance(repo.integrations, IntegrationRegistry)
    assert isinstance(repo.config, RepositoryConfig)


class TestGetIntegration:
    def test_unknown(self, local_repo, helpers):
        repo = Repository(local_repo.name, str(local_repo))

        integration = os.urandom(8).hex()
        with helpers.error(OSError, message=f'Integration does not exist: {repo.path.name}{os.sep}{integration}'):
            repo.integrations.get(integration)

    @pytest.mark.parametrize(
        "integration",
        # These are the directories that are not itnegrations nor packages
        ["docs", "datadog_checks_tests_helper"],
    )
    def test_invalid(self, local_repo, helpers, integration):
        repo = Repository(local_repo.name, str(local_repo))

        with helpers.error(
            OSError, message=f'Path is not an integration nor a Python package: {repo.path.name}{os.sep}{integration}'
        ):
            repo.integrations.get(integration)

    def test_valid(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration = repo.integrations.get('postgres')
        assert isinstance(integration, Integration)


def is_integration(repo: Repository, path: Path) -> bool:
    is_valid_directory = path.is_dir() and not path.name.startswith('.')
    has_manifest = (path / 'manifest.json').is_file()
    overrides_integration = cast(bool, repo.config.get(f'/overrides/is-integration/{path.name}', default=True))
    return is_valid_directory and (has_manifest or overrides_integration)


def is_package(repo: Repository, path: Path) -> bool:
    is_valid_directory = path.is_dir() and not path.name.startswith('.')
    has_project_file = (path / 'pyproject.toml').is_file()
    return is_valid_directory and has_project_file


class TestIntegrationsIteration:
    iter_test_params = [
        pytest.param(
            "iter",
            lambda repo, path: is_integration(repo, path)
            # Is not a worktree
            and not (path / ".git").is_file(),
            id="only integrations",
        ),
        pytest.param(
            "iter_all",
            lambda repo, path: (is_integration(repo, path) or is_package(repo, path))
            # Is not a worktree
            and not (path / ".git").is_file(),
            id="all valid",
        ),
        pytest.param(
            "iter_packages",
            lambda repo, path: is_package(repo, path)
            # Is not a worktree
            and not (path / ".git").is_file(),
            id="packages",
        ),
        pytest.param(
            "iter_tiles",
            lambda repo, path: is_integration(repo, path)
            and not is_package(repo, path)
            # Is not a worktree
            and not (path / ".git").is_file(),
            id="tiles",
        ),
        pytest.param(
            "iter_testable",
            lambda repo, path: (path / 'hatch.toml').is_file()
            # Is not a worktree
            and not (path / ".git").is_file(),
            id="testable",
        ),
        pytest.param(
            "iter_shippable",
            lambda repo, path: is_package(repo, path)
            and path.name not in NOT_SHIPPABLE
            # Is not a worktree
            and not (path / ".git").is_file(),
            id="shippable",
        ),
        pytest.param(
            "iter_agent_checks",
            lambda repo, path: (
                package_root := path / 'datadog_checks' / path.name.replace('-', '_') / '__init__.py'
            ).is_file()
            and package_root.read_text().count('import ') > 1
            # Is not a worktree
            and not (path / ".git").is_file(),
            id="agent checks",
        ),
        pytest.param(
            "iter_jmx_checks",
            lambda repo, path: (
                (path / 'datadog_checks' / path.name.replace('-', '_') / 'data' / 'metrics.yaml').is_file()
            )
            # Is not a worktree
            and not (path / ".git").is_file(),
            id="jmx checks",
        ),
    ]

    @pytest.mark.parametrize(
        "method_name, integration_filter",
        iter_test_params,
    )
    def test_integrations_iteration_default_changed(self, method_name, integration_filter, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = sorted(path.name for path in repository.path.iterdir() if integration_filter(repo, path))

        integration = integration_names[0]
        (repo.path / integration / 'foo.txt').touch()

        changed = [integration]
        iter_method = getattr(repo.integrations, method_name)
        integrations = list(iter_method())

        assert [integration.name for integration in integrations] == changed
        assert list(iter_method()) == integrations

    @pytest.mark.parametrize(
        "method_name, integration_filter",
        iter_test_params,
    )
    def test_integrations_iteration_selection(self, method_name, integration_filter, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = sorted(path.name for path in local_repo.iterdir() if integration_filter(repo, path))

        selection = [integration_names[0]]
        iter_method = getattr(repo.integrations, method_name)
        integrations = list(iter_method(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(iter_method(selection)) == integrations

    def test_integrations_iteration_selection_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        (repo.path / 'tekton' / 'foo.txt').touch()
        selection = ['changed']
        integrations = list(repo.integrations.iter(selection))

        assert [integration.name for integration in integrations] == ["tekton"]

    @pytest.mark.parametrize(
        "method_name, integration_filter",
        iter_test_params,
    )
    def test_integrations_iteration_select_all(self, method_name, integration_filter, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = sorted(path.name for path in local_repo.iterdir() if integration_filter(repo, path))

        selection = ['all']
        iter_method = getattr(repo.integrations, method_name)
        integrations = list(iter_method(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(iter_method(selection)) == integrations


class TestIterationChanged:
    def test(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        new_integration = repo.path / 'new'
        new_integration.mkdir()
        (new_integration / 'manifest.json').touch()

        (repo.path / 'datadog_checks_base' / 'README.md').remove()
        (repo.path / 'postgres' / 'README.md').remove()

        integrations = list(repo.integrations.iter_changed())
        assert [integration.name for integration in integrations] == ['datadog_checks_base', 'new', 'postgres']
        assert list(repo.integrations.iter_changed()) == integrations
