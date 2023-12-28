# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from ddev.repo.core import Repository
from ddev.utils.fs import Path


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


class TestPackageFiles:
    def test_base_package_file(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('datadog_checks_base')

        expected_files = []
        for root, _, files in os.walk(integration.package_directory):
            for f in files:
                if f.endswith(".py"):
                    expected_files.append(Path(root, f))

        assert list(integration.package_files()) == expected_files

    def test_tile_only_package_file(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('agent_metrics')

        assert not list(integration.package_files())


class TestReleaseTagPattern:
    def test_shipped(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('datadog_checks_base')

        assert integration.release_tag_pattern == r'datadog_checks_base-\d+\.\d+\.\d+'

    def test_ddev(self, local_repo):
        repo = Repository(local_repo.name, str(local_repo))
        integration = repo.integrations.get('ddev')

        assert integration.release_tag_pattern == r'ddev-v\d+\.\d+\.\d+'


class TestMetrics:
    def test_has_metrics(self, fake_repo):
        integration = fake_repo.integrations.get('dummy')

        metrics = list(integration.metrics)
        assert len(metrics) == 1
        metric = metrics[0]
        assert metric.metric_name == 'dummy.metric'
        assert metric.metric_type == 'gauge'
        assert metric.interval == 10
        assert metric.unit_name == 'seconds'
        assert metric.per_unit_name == 'object'
        assert metric.description == 'description'
        assert metric.orientation == 0
        assert metric.integration == 'dummy'
        assert metric.short_name == 'short'
        assert metric.curated_metric == ''

    def test_has_no_metrics(self, fake_repo):
        integration = fake_repo.integrations.get('no_metrics')
        assert not list(integration.metrics)

    def test_has_no_metadata_file(self, fake_repo):
        integration = fake_repo.integrations.get('no_metadata_file')
        assert not list(integration.metrics)
