# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

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


class TestIterationOnlyIntegrations:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = []
        for path in repository.path.iterdir():
            if (path / 'manifest.json').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        integration = integration_names[0]
        (repository.path / integration / 'foo.txt').touch()

        changed = [integration]
        integrations = list(repo.integrations.iter())

        assert [integration.name for integration in integrations] == changed
        assert list(repo.integrations.iter()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'manifest.json').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = [integration_names[0]]
        integrations = list(repo.integrations.iter(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(repo.integrations.iter(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'manifest.json').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = ['all']
        integrations = list(repo.integrations.iter(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(repo.integrations.iter(selection)) == integrations


class TestIterationAllValid:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = []
        for path in repository.path.iterdir():
            if (path / 'manifest.json').is_file() or (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        integration = integration_names[0]
        (repository.path / integration / 'foo.txt').touch()

        changed = [integration]
        integrations = list(repo.integrations.iter_all())

        assert [integration.name for integration in integrations] == changed
        assert list(repo.integrations.iter_all()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'manifest.json').is_file() or (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = [integration_names[0]]
        integrations = list(repo.integrations.iter_all(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(repo.integrations.iter_all(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'manifest.json').is_file() or (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = ['all']
        integrations = list(repo.integrations.iter_all(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(repo.integrations.iter_all(selection)) == integrations


class TestIterationPackages:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = []
        for path in repository.path.iterdir():
            if (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        integration = integration_names[0]
        (repository.path / integration / 'foo.txt').touch()

        changed = [integration]
        integrations = list(repo.integrations.iter_packages())

        assert [integration.name for integration in integrations] == changed
        assert list(repo.integrations.iter_packages()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = [integration_names[0]]
        integrations = list(repo.integrations.iter_packages(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(repo.integrations.iter_packages(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = ['all']
        integrations = list(repo.integrations.iter_packages(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(repo.integrations.iter_packages(selection)) == integrations


class TestIterationTiles:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = []
        for path in repository.path.iterdir():
            if (path / 'manifest.json').is_file() and not (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        integration = integration_names[0]
        (repository.path / integration / 'foo.txt').touch()

        changed = [integration]
        integrations = list(repo.integrations.iter_tiles())

        assert [integration.name for integration in integrations] == changed
        assert list(repo.integrations.iter_tiles()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'manifest.json').is_file() and not (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = [integration_names[0]]
        integrations = list(repo.integrations.iter_tiles(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(repo.integrations.iter_tiles(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'manifest.json').is_file() and not (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = ['all']
        integrations = list(repo.integrations.iter_tiles(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(repo.integrations.iter_tiles(selection)) == integrations


class TestIterationTestable:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = []
        for path in repository.path.iterdir():
            # TODO: remove tox when the Hatch migration is complete
            if (path / 'hatch.toml').is_file() or (path / 'tox.ini').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        integration = integration_names[0]
        (repository.path / integration / 'foo.txt').touch()

        changed = [integration]
        integrations = list(repo.integrations.iter_testable())

        assert [integration.name for integration in integrations] == changed
        assert list(repo.integrations.iter_testable()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            # TODO: remove tox when the Hatch migration is complete
            if (path / 'hatch.toml').is_file() or (path / 'tox.ini').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = [integration_names[0]]
        integrations = list(repo.integrations.iter_testable(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(repo.integrations.iter_testable(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            # TODO: remove tox when the Hatch migration is complete
            if (path / 'hatch.toml').is_file() or (path / 'tox.ini').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = ['all']
        integrations = list(repo.integrations.iter_testable(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(repo.integrations.iter_testable(selection)) == integrations


class TestIterationShippable:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = []
        for path in repository.path.iterdir():
            if (path / 'pyproject.toml').is_file() and path.name not in NOT_SHIPPABLE:
                integration_names.append(path.name)
        integration_names.sort()

        integration = integration_names[0]
        (repository.path / integration / 'foo.txt').touch()

        changed = [integration]
        integrations = list(repo.integrations.iter_shippable())

        assert [integration.name for integration in integrations] == changed
        assert list(repo.integrations.iter_shippable()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'pyproject.toml').is_file() and path.name not in NOT_SHIPPABLE:
                integration_names.append(path.name)
        integration_names.sort()

        selection = [integration_names[0]]
        integrations = list(repo.integrations.iter_shippable(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(repo.integrations.iter_shippable(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'pyproject.toml').is_file() and path.name not in NOT_SHIPPABLE:
                integration_names.append(path.name)
        integration_names.sort()

        selection = ['all']
        integrations = list(repo.integrations.iter_shippable(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(repo.integrations.iter_shippable(selection)) == integrations


class TestIterationAgentChecks:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = []
        for path in repository.path.iterdir():
            if (
                package_root := path / 'datadog_checks' / path.name.replace('-', '_') / '__init__.py'
            ).is_file() and package_root.read_text().count('import ') > 1:
                integration_names.append(path.name)
        integration_names.sort()

        integration = integration_names[0]
        (repository.path / integration / 'foo.txt').touch()

        changed = [integration]
        integrations = list(repo.integrations.iter_agent_checks())

        assert [integration.name for integration in integrations] == changed
        assert list(repo.integrations.iter_agent_checks()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (
                package_root := path / 'datadog_checks' / path.name.replace('-', '_') / '__init__.py'
            ).is_file() and package_root.read_text().count('import ') > 1:
                integration_names.append(path.name)
        integration_names.sort()

        selection = [integration_names[0]]
        integrations = list(repo.integrations.iter_agent_checks(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(repo.integrations.iter_agent_checks(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (
                package_root := path / 'datadog_checks' / path.name.replace('-', '_') / '__init__.py'
            ).is_file() and package_root.read_text().count('import ') > 1:
                integration_names.append(path.name)
        integration_names.sort()

        selection = ['all']
        integrations = list(repo.integrations.iter_agent_checks(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(repo.integrations.iter_agent_checks(selection)) == integrations


class TestIterationJMXChecks:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = []
        for path in repository.path.iterdir():
            if (path / 'datadog_checks' / path.name.replace('-', '_') / 'data' / 'metrics.yaml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        integration = integration_names[0]
        (repository.path / integration / 'foo.txt').touch()

        changed = [integration]
        integrations = list(repo.integrations.iter_jmx_checks())

        assert [integration.name for integration in integrations] == changed
        assert list(repo.integrations.iter_jmx_checks()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'datadog_checks' / path.name.replace('-', '_') / 'data' / 'metrics.yaml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = [integration_names[0]]
        integrations = list(repo.integrations.iter_jmx_checks(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(repo.integrations.iter_jmx_checks(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = []
        for path in local_repo.iterdir():
            if (path / 'datadog_checks' / path.name.replace('-', '_') / 'data' / 'metrics.yaml').is_file():
                integration_names.append(path.name)
        integration_names.sort()

        selection = ['all']
        integrations = list(repo.integrations.iter_jmx_checks(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(repo.integrations.iter_jmx_checks(selection)) == integrations


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
