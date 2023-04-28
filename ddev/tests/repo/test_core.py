# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig
from ddev.repo.constants import NOT_SHIPPABLE
from ddev.repo.core import IntegrationRegistry, Repository


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

    def test_invalid(self, local_repo, helpers):
        repo = Repository(local_repo.name, str(local_repo))

        integration = '.github'
        with helpers.error(
            OSError, message=f'Path is not an integration nor a Python package: {repo.path.name}{os.sep}{integration}'
        ):
            repo.integrations.get(integration)

    def test_valid(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration = repo.integrations.get('postgres')
        assert isinstance(integration, Integration)


class TestIntegrationsIteration:

    iter_test_params = [
        pytest.param("iter", lambda path: (path / 'manifest.json').is_file(), id="only integrations"),
        pytest.param(
            "iter_all",
            lambda path: (path / 'manifest.json').is_file() or (path / 'pyproject.toml').is_file(),
            id="all valid",
        ),
        pytest.param("iter_packages", lambda path: (path / 'pyproject.toml').is_file(), id="packages"),
        pytest.param(
            "iter_tiles",
            lambda path: (path / 'manifest.json').is_file() and not (path / 'pyproject.toml').is_file(),
            id="tiles",
        ),
        # TODO: remove tox when the Hatch migration is complete
        pytest.param(
            "iter_testable", lambda path: (path / 'hatch.toml').is_file() or (path / 'tox.ini').is_file(), id="testable"
        ),
        pytest.param(
            "iter_shippable",
            lambda path: (path / 'pyproject.toml').is_file() and path.name not in NOT_SHIPPABLE,
            id="shippable",
        ),
        pytest.param(
            "iter_agent_checks",
            lambda path: (
                package_root := path / 'datadog_checks' / path.name.replace('-', '_') / '__init__.py'
            ).is_file()
            and package_root.read_text().count('import ') > 1,
            id="agent checks",
        ),
        pytest.param(
            "iter_jmx_checks",
            lambda path: (path / 'datadog_checks' / path.name.replace('-', '_') / 'data' / 'metrics.yaml').is_file(),
            id="jmx checks",
        ),
    ]

    @pytest.mark.parametrize(
        "method_name, integration_filter",
        iter_test_params,
    )
    def test_integrations_iteration_default_changed(self, method_name, integration_filter, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = sorted(path.name for path in repository.path.iterdir() if integration_filter(path))

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

        integration_names = sorted(path.name for path in local_repo.iterdir() if integration_filter(path))

        selection = [integration_names[0]]
        iter_method = getattr(repo.integrations, method_name)
        integrations = list(iter_method(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(iter_method(selection)) == integrations

    @pytest.mark.parametrize(
        "method_name, integration_filter",
        iter_test_params,
    )
    def test_integrations_iteration_select_all(self, method_name, integration_filter, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = sorted(path.name for path in local_repo.iterdir() if integration_filter(path))

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
