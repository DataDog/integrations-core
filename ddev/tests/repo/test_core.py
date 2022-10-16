# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig
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
