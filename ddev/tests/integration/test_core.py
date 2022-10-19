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


class TestIsIntegration:
    def test_integration(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('postgres')

        assert integration.is_integration is True

    def test_not_integration(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('datadog_checks_downloader')

        assert integration.is_integration is False


class TestIsPackage:
    def test_package(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('postgres')

        assert integration.is_package is True

    def test_tile(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('kubernetes')

        assert integration.is_package is False


class TestIsTile:
    def test_tile(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('kubernetes')

        assert integration.is_tile is True

    def test_check(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('postgres')

        assert integration.is_tile is False


class TestIsTestable:
    def test_check(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('postgres')

        assert integration.is_testable is True

    def test_tile(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('kubernetes')

        assert integration.is_testable is False


class TestIsShippable:
    def test_check(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('postgres')

        assert integration.is_shippable is True

    def test_tile(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('kubernetes')

        assert integration.is_shippable is False

    def test_excluded(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('datadog_checks_dev')

        assert integration.is_shippable is False


class TestIsAgentCheck:
    def test_check(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('postgres')

        assert integration.is_agent_check is True

    def test_not_check(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('datadog_checks_base')

        assert integration.is_agent_check is False

    def test_tile(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('kubernetes')

        assert integration.is_agent_check is False

    def test_dual_jmx_check(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('hazelcast')

        assert integration.is_agent_check is True


class TestIsJMXCheck:
    def test_agent_check(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('postgres')

        assert integration.is_jmx_check is False

    def test_jmx_only(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('cassandra')

        assert integration.is_jmx_check is True

    def test_dual_agent_check(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('hazelcast')

        assert integration.is_jmx_check is True


class TestPackageDirectory:
    def test_ddev(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('ddev')

        assert integration.package_directory == local_repo / integration.name / 'src' / 'ddev'

    def test_base_package(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('datadog_checks_base')

        assert integration.package_directory == local_repo / integration.name / 'datadog_checks' / 'base'

    def test_dev_package(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('datadog_checks_dev')

        assert integration.package_directory == local_repo / integration.name / 'datadog_checks' / 'dev'

    def test_downloader(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('datadog_checks_downloader')

        assert integration.package_directory == local_repo / integration.name / 'datadog_checks' / 'downloader'

    def test_normalization(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('go-metro')

        assert integration.package_directory == local_repo / integration.name / 'datadog_checks' / 'go_metro'
