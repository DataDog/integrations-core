# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import requests

from datadog_checks.vault import Vault
from .common import INSTANCES, MockResponse


class TestVault:
    def test_bad_config(self, aggregator):
        instance = INSTANCES['invalid']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])
        c.check(instance)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, count=0)

    def test_service_check_connect_ok(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])
        c.check(instance)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)

    def test_service_check_connect_ok_all_tags(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])

        config = c.get_config(instance)

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == config['api_url'] + '/sys/leader':
                return MockResponse({
                    'ha_enabled': False,
                    'is_self': True,
                    'leader_address': '',
                    'leader_cluster_address': ''
                })
            elif url == config['api_url'] + '/sys/health':
                return MockResponse({
                    'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                    'cluster_name': 'vault-cluster-f5f44063',
                    'initialized': True,
                    'replication_dr_mode': 'disabled',
                    'replication_performance_mode': 'disabled',
                    'sealed': False,
                    'server_time_utc': 1529357080,
                    'standby': False,
                    'version': '0.10.2'
                })
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            c.check(instance)

        expected_tags = [
            'instance:foobar',
            'is_leader:true',
            'cluster_name:vault-cluster-f5f44063',
            'vault_version:0.10.2'
        ]
        aggregator.assert_service_check(
            Vault.SERVICE_CHECK_CONNECT,
            status=Vault.OK,
            tags=expected_tags,
            count=1
        )

    def test_service_check_connect_fail(self, aggregator):
        instance = INSTANCES['bad_url']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])
        c.check(instance)

        aggregator.assert_service_check(
            Vault.SERVICE_CHECK_CONNECT,
            status=Vault.CRITICAL,
            tags=['instance:foobar'],
            count=1
        )

    def test_service_check_unsealed_ok(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])
        c.check(instance)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.OK, count=1)

    def test_service_check_unsealed_ok_all_tags(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])

        config = c.get_config(instance)

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == config['api_url'] + '/sys/leader':
                return MockResponse({
                    'ha_enabled': False,
                    'is_self': True,
                    'leader_address': '',
                    'leader_cluster_address': ''
                })
            elif url == config['api_url'] + '/sys/health':
                return MockResponse({
                    'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                    'cluster_name': 'vault-cluster-f5f44063',
                    'initialized': True,
                    'replication_dr_mode': 'disabled',
                    'replication_performance_mode': 'disabled',
                    'sealed': False,
                    'server_time_utc': 1529357080,
                    'standby': False,
                    'version': '0.10.2'
                })
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            c.check(instance)

        expected_tags = [
            'instance:foobar',
            'is_leader:true',
            'cluster_name:vault-cluster-f5f44063',
            'vault_version:0.10.2'
        ]
        aggregator.assert_service_check(
            Vault.SERVICE_CHECK_UNSEALED,
            status=Vault.OK,
            tags=expected_tags,
            count=1
        )

    def test_service_check_unsealed_fail(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])

        config = c.get_config(instance)

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == config['api_url'] + '/sys/health':
                return MockResponse({
                    'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                    'cluster_name': 'vault-cluster-f5f44063',
                    'initialized': False,
                    'replication_dr_mode': 'disabled',
                    'replication_performance_mode': 'disabled',
                    'sealed': True,
                    'server_time_utc': 1529357080,
                    'standby': False,
                    'version': '0.10.2'
                })
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            c.check(instance)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.CRITICAL, count=1)

    def test_service_check_initialized_ok(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])
        c.check(instance)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, count=1)

    def test_service_check_initialized_ok_all_tags(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])

        config = c.get_config(instance)

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == config['api_url'] + '/sys/leader':
                return MockResponse({
                    'ha_enabled': False,
                    'is_self': True,
                    'leader_address': '',
                    'leader_cluster_address': ''
                })
            elif url == config['api_url'] + '/sys/health':
                return MockResponse({
                    'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                    'cluster_name': 'vault-cluster-f5f44063',
                    'initialized': True,
                    'replication_dr_mode': 'disabled',
                    'replication_performance_mode': 'disabled',
                    'sealed': False,
                    'server_time_utc': 1529357080,
                    'standby': False,
                    'version': '0.10.2'
                })
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            c.check(instance)

        expected_tags = [
            'instance:foobar',
            'is_leader:true',
            'cluster_name:vault-cluster-f5f44063',
            'vault_version:0.10.2'
        ]
        aggregator.assert_service_check(
            Vault.SERVICE_CHECK_INITIALIZED,
            status=Vault.OK,
            tags=expected_tags,
            count=1
        )

    def test_service_check_initialized_fail(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])

        config = c.get_config(instance)

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == config['api_url'] + '/sys/health':
                return MockResponse({
                    'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                    'cluster_name': 'vault-cluster-f5f44063',
                    'initialized': False,
                    'replication_dr_mode': 'disabled',
                    'replication_performance_mode': 'disabled',
                    'sealed': False,
                    'server_time_utc': 1529357080,
                    'standby': False,
                    'version': '0.10.2'
                })
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            c.check(instance)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.CRITICAL, count=1)

    def test_event_leader_change(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])

        config = c.get_config(instance)
        config['leader'] = 'foo'

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == config['api_url'] + '/sys/leader':
                return MockResponse({
                    'ha_enabled': False,
                    'is_self': True,
                    'leader_address': 'bar',
                    'leader_cluster_address': ''
                })
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            c.check(instance)

        assert len(aggregator.events) > 0

        event = aggregator.events[0]
        assert event['event_type'] == Vault.EVENT_LEADER_CHANGE
        assert event['msg_title'] == 'Leader change'
        assert event['msg_text'] == 'Leader changed from `foo` to `bar`.'
        assert event['alert_type'] == 'info'
        assert event['source_type_name'] == Vault.CHECK_NAME
        assert event['host'] == c.hostname
        assert 'is_leader:true' in event['tags']

    def test_is_leader_metric_true(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])

        config = c.get_config(instance)

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == config['api_url'] + '/sys/leader':
                return MockResponse({
                    'ha_enabled': False,
                    'is_self': True,
                    'leader_address': 'bar',
                    'leader_cluster_address': ''
                })
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            c.check(instance)

        aggregator.assert_metric('vault.is_leader', 1)

    def test_is_leader_metric_false(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, None, {}, [instance])

        config = c.get_config(instance)

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == config['api_url'] + '/sys/leader':
                return MockResponse({
                    'ha_enabled': False,
                    'is_self': False,
                    'leader_address': 'bar',
                    'leader_cluster_address': ''
                })
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            c.check(instance)

        aggregator.assert_metric('vault.is_leader', 0)
