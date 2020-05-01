# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import mock
import pytest
import requests

from datadog_checks.vault import Vault
from datadog_checks.vault.errors import ApiUnreachable
from datadog_checks.vault.vault import Leader

from .common import INSTANCES, MockResponse, auth_required, noauth_required
from .utils import run_check

pytestmark = pytest.mark.usefixtures('dd_environment')


class TestVault:
    def test_bad_config(self, aggregator):
        instance = INSTANCES['invalid']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(Exception, match='^Vault setting `api_url` is required$'):
            run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, count=0)

    def test_unsupported_api_version_fallback(self, aggregator):
        instance = INSTANCES['unsupported_api']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        assert not instance['api_url'].endswith(Vault.DEFAULT_API_VERSION)
        run_check(c)
        assert c._api_url.endswith(Vault.DEFAULT_API_VERSION)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)

    def test_service_check_connect_ok(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)

    def test_service_check_connect_ok_all_tags(self, aggregator, global_tags):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    {'ha_enabled': False, 'is_self': True, 'leader_address': '', 'leader_cluster_address': ''}
                )
            elif url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    {
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': True,
                        'replication_dr_mode': 'disabled',
                        'replication_performance_mode': 'disabled',
                        'sealed': False,
                        'server_time_utc': 1529357080,
                        'standby': False,
                        'version': '0.10.2',
                    }
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, tags=global_tags, count=1)

    def test_service_check_connect_fail(self, aggregator):
        instance = INSTANCES['bad_url']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(
            Exception,
            match=r'^Vault endpoint `{}.+?` timed out after 1\.0 seconds$'.format(re.escape(instance['api_url'])),
        ):
            run_check(c, extract_message=True)

        aggregator.assert_service_check(
            Vault.SERVICE_CHECK_CONNECT,
            status=Vault.CRITICAL,
            tags=['instance:foobar', 'api_url:http://1.2.3.4:555/v1'],
            count=1,
        )

    def test_service_check_500_fail(self, aggregator, global_tags):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with mock.patch('requests.get', return_value=MockResponse('', status_code=500)):
            with pytest.raises(
                Exception, match=r'^The Vault endpoint `{}.+?` returned 500$'.format(re.escape(instance['api_url'])),
            ):
                run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, tags=global_tags, count=1)

    def test_api_unreachable(self):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(ApiUnreachable, match=r"Error accessing Vault endpoint.*"):
            c.access_api("http://foo.bar", ignore_status_codes=None)

    def test_service_check_unsealed_ok(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.OK, count=1)

    def test_service_check_unsealed_ok_all_tags(self, aggregator, global_tags):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    {'ha_enabled': False, 'is_self': True, 'leader_address': '', 'leader_cluster_address': ''}
                )
            elif url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    {
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': True,
                        'replication_dr_mode': 'disabled',
                        'replication_performance_mode': 'disabled',
                        'sealed': False,
                        'server_time_utc': 1529357080,
                        'standby': False,
                        'version': '0.10.2',
                    }
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        expected_tags = ['is_leader:true', 'cluster_name:vault-cluster-f5f44063', 'vault_version:0.10.2']
        expected_tags.extend(global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.OK, tags=expected_tags, count=1)

    def test_service_check_unsealed_fail(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    {
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': False,
                        'replication_dr_mode': 'disabled',
                        'replication_performance_mode': 'disabled',
                        'sealed': True,
                        'server_time_utc': 1529357080,
                        'standby': False,
                        'version': '0.10.2',
                    },
                    status_code=503,
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.CRITICAL, count=1)

    def test_service_check_initialized_ok(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, count=1)

    def test_service_check_initialized_ok_all_tags(self, aggregator, global_tags):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    {'ha_enabled': False, 'is_self': True, 'leader_address': '', 'leader_cluster_address': ''}
                )
            elif url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    {
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': True,
                        'replication_dr_mode': 'disabled',
                        'replication_performance_mode': 'disabled',
                        'sealed': False,
                        'server_time_utc': 1529357080,
                        'standby': False,
                        'version': '0.10.2',
                    }
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        expected_tags = ['is_leader:true', 'cluster_name:vault-cluster-f5f44063', 'vault_version:0.10.2']
        expected_tags.extend(global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, tags=expected_tags, count=1)

    def test_service_check_initialized_fail(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    {
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': False,
                        'replication_dr_mode': 'disabled',
                        'replication_performance_mode': 'disabled',
                        'sealed': False,
                        'server_time_utc': 1529357080,
                        'standby': False,
                        'version': '0.10.2',
                    },
                    status_code=501,
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.CRITICAL, count=1)

    @pytest.mark.parametrize("cluster", [True, False])
    def test_event_leader_change(self, aggregator, cluster):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        if cluster:
            c._previous_leader = Leader('', 'foo')
        else:
            c._previous_leader = Leader('foo', '')

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                if cluster:
                    leader_addr = ''
                    leader_cluster_addr = 'bar'
                else:
                    leader_addr = 'bar'
                    leader_cluster_addr = ''
                return MockResponse(
                    {
                        'ha_enabled': False,
                        'is_self': True,
                        'leader_address': leader_addr,
                        'leader_cluster_address': leader_cluster_addr,
                    }
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        assert len(aggregator.events) > 0

        event = aggregator.events[0]
        assert event['event_type'] == Vault.EVENT_LEADER_CHANGE
        assert event['msg_title'] == 'Leader change'
        if cluster:
            assert event['msg_text'] == 'Leader cluster address changed from `foo` to `bar`.'
        else:
            assert event['msg_text'] == 'Leader address changed from `foo` to `bar`.'
        assert event['alert_type'] == 'info'
        assert event['source_type_name'] == Vault.CHECK_NAME
        assert event['host'] == c.hostname
        assert 'is_leader:true' in event['tags']

    def test_leader_change_not_self(self, aggregator):
        """The agent should only submit a leader change event when the monitored vault is the leader."""
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        c._previous_leader = Leader('foo', '')

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    {'ha_enabled': False, 'is_self': False, 'leader_address': 'bar', 'leader_cluster_address': ''}
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        assert len(aggregator.events) == 0

    def test_is_leader_metric_true(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    {'ha_enabled': False, 'is_self': True, 'leader_address': 'bar', 'leader_cluster_address': ''}
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        aggregator.assert_metric('vault.is_leader', 1)

    def test_is_leader_metric_false(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    {'ha_enabled': False, 'is_self': False, 'leader_address': 'bar', 'leader_cluster_address': ''}
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        aggregator.assert_metric('vault.is_leader', 0)

    @pytest.mark.parametrize('status_code', [200, 429, 472, 473, 501, 503])
    def test_sys_health_non_standard_status_codes(self, aggregator, status_code):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    {
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': False,
                        'replication_dr_mode': 'disabled',
                        'replication_performance_mode': 'disabled',
                        'sealed': False,
                        'server_time_utc': 1529357080,
                        'standby': True,
                        'performance_standby': False,
                        'version': '0.10.2',
                    },
                    status_code=status_code,
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        aggregator.assert_metric('vault.is_leader', 1)
        aggregator.assert_all_metrics_covered()

    def test_sys_leader_non_standard_status_codes(self, aggregator):
        instance = INSTANCES['main']
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse({'errors': ["Vault is sealed"]}, status_code=503)
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            run_check(c)

        aggregator.assert_metric('vault.is_leader', count=0)

    @auth_required
    def test_token_renewal(self, caplog, aggregator, instance, global_tags):
        instance = instance()
        instance['token_renewal_wait'] = 1
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        renew_client_token = c.renew_client_token

        run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)
        assert 'Permission denied, refreshing the client token...' not in caplog.text

        c.set_client_token('foo')
        c.renew_client_token = lambda: None
        aggregator.reset()

        run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)
        assert 'Permission denied, refreshing the client token...' in caplog.text

        aggregator.reset()

        with pytest.raises(Exception, match='^403 Client Error: Forbidden for url'):
            run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=1, tags=global_tags)

        renew_client_token()
        aggregator.reset()

        run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)

    @auth_required
    def test_auth_needed_but_no_token(self, aggregator, instance, global_tags):
        instance = instance()
        instance['no_token'] = True
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(Exception, match='^400 Client Error: Bad Request for url'):
            run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=1, tags=global_tags)

    @noauth_required
    def test_noauth_needed(self, aggregator, no_token_instance, global_tags):
        c = Vault(Vault.CHECK_NAME, {}, [no_token_instance])
        run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)
