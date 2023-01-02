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


class BaseIterationTest:
    def test_default_changed(self, repository):
        repo = Repository(repository.path.name, str(repository.path))

        integration_names = self.integration_names(repository.path)

        integration = integration_names[0]
        (repo.path / integration / 'foo.txt').touch()

        changed = [integration]
        iter_method = self.iter_method(repo)
        integrations = list(iter_method())

        assert [integration.name for integration in integrations] == changed
        assert list(iter_method()) == integrations

    def test_selection(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = self.integration_names(local_repo)

        selection = [integration_names[0]]
        iter_method = self.iter_method(repo)
        integrations = list(iter_method(selection))

        assert [integration.name for integration in integrations] == selection
        assert list(iter_method(selection)) == integrations

    def test_all(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))

        integration_names = self.integration_names(local_repo)

        selection = ['all']
        iter_method = self.iter_method(repo)
        integrations = list(iter_method(selection))

        assert [integration.name for integration in integrations] == integration_names
        assert list(iter_method(selection)) == integrations


class TestIterationOnlyIntegrations(BaseIterationTest):
    @classmethod
    def iter_method(cls, repo):
        return repo.integrations.iter

    @classmethod
    def integration_names(cls, repository):
        integration_names = []
        for path in repository.iterdir():
            if (path / 'manifest.json').is_file():
                integration_names.append(path.name)
        integration_names.sort()
        return integration_names


class TestIterationAllValid(BaseIterationTest):
    @classmethod
    def iter_method(cls, repo):
        return repo.integrations.iter_all

    @classmethod
    def integration_names(cls, repository):
        integration_names = []
        for path in repository.iterdir():
            if (path / 'manifest.json').is_file() or (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()
        return integration_names


class TestIterationPackages(BaseIterationTest):
    @classmethod
    def iter_method(cls, repo):
        return repo.integrations.iter_packages

    @classmethod
    def integration_names(cls, repository):
        integration_names = []
        for path in repository.iterdir():
            if (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()
        return integration_names


class TestIterationTiles(BaseIterationTest):
    @classmethod
    def iter_method(cls, repo):
        return repo.integrations.iter_tiles

    @classmethod
    def integration_names(cls, repository):
        integration_names = []
        for path in repository.iterdir():
            if (path / 'manifest.json').is_file() and not (path / 'pyproject.toml').is_file():
                integration_names.append(path.name)
        integration_names.sort()
        return integration_names


class TestIterationTestable(BaseIterationTest):
    @classmethod
    def iter_method(cls, repo):
        return repo.integrations.iter_testable

    @classmethod
    def integration_names(cls, repository):
        integration_names = []
        for path in repository.iterdir():
            # TODO: remove tox when the Hatch migration is complete
            if (path / 'hatch.toml').is_file() or (path / 'tox.ini').is_file():
                integration_names.append(path.name)
        integration_names.sort()
        return integration_names


class TestIterationShippable(BaseIterationTest):
    @classmethod
    def iter_method(cls, repo):
        return repo.integrations.iter_shippable

    @classmethod
    def integration_names(cls, repository):
        integration_names = []
        for path in repository.iterdir():
            if (path / 'pyproject.toml').is_file() and path.name not in NOT_SHIPPABLE:
                integration_names.append(path.name)
        integration_names.sort()
        return integration_names


class TestIterationAgentChecks(BaseIterationTest):
    @classmethod
    def iter_method(cls, repo):
        return repo.integrations.iter_agent_checks

    @classmethod
    def integration_names(cls, repository):
        integration_names = []
        for path in repository.iterdir():
            if (
                package_root := path / 'datadog_checks' / path.name.replace('-', '_') / '__init__.py'
            ).is_file() and package_root.read_text().count('import ') > 1:
                integration_names.append(path.name)
        integration_names.sort()
        return integration_names


class TestIterationJMXChecks(BaseIterationTest):
    @classmethod
    def iter_method(cls, repo):
        return repo.integrations.iter_jmx_checks

    @classmethod
    def integration_names(cls, repository):
        integration_names = []
        for path in repository.iterdir():
            if (path / 'datadog_checks' / path.name.replace('-', '_') / 'data' / 'metrics.yaml').is_file():
                integration_names.append(path.name)
        integration_names.sort()
        return integration_names


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
