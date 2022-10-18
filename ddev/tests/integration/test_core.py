# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.repo.core import Repository


def test_attributes(local_repo, valid_integration):
    repo = Repository(local_repo.name, str(local_repo))
    integration = repo.integrations.get(valid_integration)

    expected_path = repo.path / valid_integration
    assert integration.path == expected_path
    assert integration.name == expected_path.name
    assert integration.repo_path is repo.path
    assert integration.repo_config is repo.config


class TestDisplayName:
    def test_integration(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('redisdb')

        assert integration.display_name == 'Redis'

    def test_integration_override(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('nginx')

        assert integration.display_name == 'NGINX'

    def test_not_integration_directory_name(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('ddev')

        assert integration.display_name == 'ddev'
