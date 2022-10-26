# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import mock
import pytest
import requests
from six.moves.urllib.parse import urlparse

from datadog_checks.dev.http import MockResponse
from datadog_checks.vault import Vault
from datadog_checks.vault.common import DEFAULT_API_VERSION
from datadog_checks.vault.errors import ApiUnreachable
from datadog_checks.vault.vault import Leader

from .common import INSTANCES, auth_required, noauth_required
from .metrics import MERKLE_WAL_METRICS, MERKLE_WAL_QUANTILES
from .utils import assert_all_metrics, get_fixture_path

pytestmark = pytest.mark.usefixtures('dd_environment')


class TestVault:
    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_bad_config(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['invalid'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(Exception):
            dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, count=0)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_unsupported_api_version_fallback(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['unsupported_api'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        assert not instance['api_url'].endswith(DEFAULT_API_VERSION)
        dd_run_check(c)
        assert c._api_url.endswith(DEFAULT_API_VERSION)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_connect_ok(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        dd_run_check(c, dd_run_check)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_connect_ok_all_tags(self, aggregator, dd_run_check, global_tags, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    json_data={'ha_enabled': False, 'is_self': True, 'leader_address': '', 'leader_cluster_address': ''}
                )
            elif url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
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
            dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, tags=global_tags, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_connect_fail(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['bad_url'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        if use_openmetrics:
            hostname = urlparse(instance['api_url']).hostname
            expected_exception = r'Connection to {} timed out'.format(hostname)

        else:
            expected_exception = r'^Vault endpoint `{}.+?` timed out after 1\.0 seconds$'.format(
                re.escape(instance['api_url'])
            )

        with pytest.raises(
            Exception,
            match=expected_exception,
        ):
            dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(
            Vault.SERVICE_CHECK_CONNECT,
            status=Vault.CRITICAL,
            tags=['instance:foobar', 'api_url:http://1.2.3.4:555/v1'],
            count=1,
        )

    def test_service_check_500_fail(self, aggregator, dd_run_check, global_tags):
        instance = {'use_openmetrics': False}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with mock.patch('requests.get', return_value=MockResponse(status_code=500)):
            with pytest.raises(
                Exception, match=r'^The Vault endpoint `{}.+?` returned 500$'.format(re.escape(instance['api_url']))
            ):
                dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, tags=global_tags, count=1)

    def test_api_unreachable(self):
        instance = {'use_openmetrics': False}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(ApiUnreachable, match=r"Error accessing Vault endpoint.*"):
            c.access_api("http://foo.bar", ignore_status_codes=None)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_unsealed_ok(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.OK, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_unsealed_ok_all_tags(self, aggregator, dd_run_check, global_tags, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    json_data={'ha_enabled': False, 'is_self': True, 'leader_address': '', 'leader_cluster_address': ''}
                )
            elif url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
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
            dd_run_check(c)

        expected_tags = [
            'is_leader:true',
            'vault_cluster:vault-cluster-f5f44063',
            'vault_version:0.10.2',
        ]
        if not use_openmetrics:
            expected_tags.append('cluster_name:vault-cluster-f5f44063')
        expected_tags.extend(global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.OK, tags=expected_tags, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_unsealed_fail(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
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
            dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.CRITICAL, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_initialized_ok(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_initialized_ok_all_tags(self, aggregator, dd_run_check, global_tags, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    json_data={'ha_enabled': False, 'is_self': True, 'leader_address': '', 'leader_cluster_address': ''}
                )
            elif url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
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
            dd_run_check(c)

        expected_tags = [
            'is_leader:true',
            'vault_cluster:vault-cluster-f5f44063',
            'vault_version:0.10.2',
        ]
        if not use_openmetrics:
            expected_tags.append('cluster_name:vault-cluster-f5f44063')
        expected_tags.extend(global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, tags=expected_tags, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_initialized_fail(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
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
            dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.CRITICAL, count=1)

    def test_disable_legacy_cluster_tag(self, aggregator, dd_run_check, global_tags):
        instance = {'disable_legacy_cluster_tag': True, 'use_openmetrics': False}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    json_data={'ha_enabled': False, 'is_self': True, 'leader_address': '', 'leader_cluster_address': ''}
                )
            elif url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
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
            dd_run_check(c)

        expected_tags = [
            'is_leader:true',
            'vault_cluster:vault-cluster-f5f44063',
            'vault_version:0.10.2',
        ]
        expected_tags.extend(global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, tags=expected_tags, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_replication_dr_mode(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        c.log.debug = mock.MagicMock()
        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': False,
                        'replication_dr_mode': 'secondary',
                        'replication_performance_mode': 'primary',
                        'sealed': False,
                        'server_time_utc': 1529357080,
                        'standby': True,
                        'performance_standby': False,
                        'version': '0.10.2',
                    },
                    status_code=200,
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            dd_run_check(c)
            c.log.debug.assert_called_with(
                "Detected vault in replication DR secondary mode, skipping Prometheus metric collection."
            )
        aggregator.assert_metric('vault.is_leader', 1)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)
        assert_all_metrics(aggregator)

    @pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
    def test_replication_dr_mode_collect_secondary(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics, 'collect_secondary_dr': True}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        c.log.debug = mock.MagicMock()
        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': False,
                        'replication_dr_mode': 'secondary',
                        'replication_performance_mode': 'primary',
                        'sealed': False,
                        'server_time_utc': 1529357080,
                        'standby': True,
                        'performance_standby': False,
                        'version': '0.10.2',
                    },
                    status_code=200,
                )
            return requests_get(url, *args, **kwargs)

        metric_collection = 'OpenMetrics' if use_openmetrics else 'Prometheus'

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            dd_run_check(c)
            c.log.debug.assert_called_with(
                "Detected vault in replication DR secondary mode but also detected that "
                "`collect_secondary_dr` is enabled, %s metric collection will still occur." % metric_collection
            )
        aggregator.assert_metric('vault.is_leader', 1)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)
        assert_all_metrics(aggregator)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_replication_dr_mode_changed(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        c.log.debug = mock.MagicMock()
        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                if getattr(mock_requests_get, 'first_health_call', True):
                    mock_requests_get.first_health_call = False
                    replication_dr_mode = 'primary'
                else:
                    replication_dr_mode = 'secondary'

                return MockResponse(
                    json_data={
                        'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
                        'cluster_name': 'vault-cluster-f5f44063',
                        'initialized': False,
                        'replication_dr_mode': replication_dr_mode,
                        'replication_performance_mode': 'primary',
                        'sealed': False,
                        'server_time_utc': 1529357080,
                        'standby': True,
                        'performance_standby': False,
                        'version': '0.10.2',
                    },
                    status_code=200,
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            dd_run_check(c)
            assert not c._skip_dr_metric_collection
            aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)
            aggregator.assert_metric('vault.is_leader', 1)
            assert_all_metrics(aggregator)
            aggregator.reset()

            dd_run_check(c)
            c.log.debug.assert_called_with(
                "Detected vault in replication DR secondary mode, skipping Prometheus metric collection."
            )
            assert c._skip_dr_metric_collection
            aggregator.assert_metric('vault.is_leader', 1)
            aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)
            assert_all_metrics(aggregator)

    @pytest.mark.parametrize("cluster", [True, False])
    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_event_leader_change(self, aggregator, dd_run_check, cluster, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        next_leader = None
        if cluster:
            c._previous_leader = Leader('', 'foo')
            next_leader = Leader('', 'bar')
        else:
            c._previous_leader = Leader('foo', '')
            next_leader = Leader('bar', '')

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    json_data={
                        'ha_enabled': False,
                        'is_self': True,
                        'leader_address': next_leader.leader_addr,
                        'leader_cluster_address': next_leader.leader_cluster_addr,
                    }
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            dd_run_check(c)

        assert len(aggregator.events) > 0

        event = aggregator.events[0]
        assert event['event_type'] == c.EVENT_LEADER_CHANGE
        assert event['msg_title'] == 'Leader change'
        if cluster:
            assert event['msg_text'] == 'Leader cluster address changed from `foo` to `bar`.'
        else:
            assert event['msg_text'] == 'Leader address changed from `foo` to `bar`.'
        assert event['alert_type'] == 'info'
        assert event['source_type_name'] == c.CHECK_NAME
        assert event['host'] == c.hostname
        assert 'is_leader:true' in event['tags']
        assert c._previous_leader == next_leader

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_leader_change_not_self(self, aggregator, dd_run_check, use_openmetrics):
        """The agent should only submit a leader change event when the monitored vault is the leader."""
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        c._previous_leader = Leader('foo', '')

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    json_data={
                        'ha_enabled': False,
                        'is_self': False,
                        'leader_address': 'bar',
                        'leader_cluster_address': '',
                    }
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            dd_run_check(c)

        assert len(aggregator.events) == 0

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_is_leader_metric_true(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    json_data={
                        'ha_enabled': False,
                        'is_self': True,
                        'leader_address': 'bar',
                        'leader_cluster_address': '',
                    }
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            dd_run_check(c)

        aggregator.assert_metric('vault.is_leader', 1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_is_leader_metric_false(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(
                    json_data={
                        'ha_enabled': False,
                        'is_self': False,
                        'leader_address': 'bar',
                        'leader_cluster_address': '',
                    }
                )
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            dd_run_check(c)

        aggregator.assert_metric('vault.is_leader', 0)

    @pytest.mark.parametrize('status_code', [200, 429, 472, 473, 501, 503])
    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_sys_health_non_standard_status_codes(self, aggregator, dd_run_check, status_code, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/health':
                return MockResponse(
                    json_data={
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
            dd_run_check(c)

        aggregator.assert_metric('vault.is_leader', 1)
        assert_all_metrics(aggregator)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_sys_leader_non_standard_status_codes(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        # Keep a reference for use during mock
        requests_get = requests.get

        def mock_requests_get(url, *args, **kwargs):
            if url == instance['api_url'] + '/sys/leader':
                return MockResponse(json_data={'errors': ["Vault is sealed"]}, status_code=503)
            return requests_get(url, *args, **kwargs)

        with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
            dd_run_check(c)

        aggregator.assert_metric('vault.is_leader', count=0)

    @auth_required
    def test_token_renewal(self, caplog, aggregator, dd_run_check, instance, global_tags):
        instance = instance()
        instance['use_openmetrics'] = False
        instance['token_renewal_wait'] = 1
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        renew_client_token = c.renew_client_token

        dd_run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)
        assert 'Permission denied, refreshing the client token...' not in caplog.text

        c.set_client_token('foo')
        c.renew_client_token = lambda: None
        aggregator.reset()

        dd_run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)
        assert 'Permission denied, refreshing the client token...' in caplog.text

        aggregator.reset()

        with pytest.raises(Exception, match='^403 Client Error: Forbidden for url'):
            dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=1, tags=global_tags)

        renew_client_token()
        aggregator.reset()

        dd_run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)

    @auth_required
    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    @pytest.mark.parametrize('use_auth_file', [False, True])
    def test_auth_needed_but_no_token(
        self, aggregator, dd_run_check, instance, global_tags, use_openmetrics, use_auth_file
    ):
        instance = instance(use_auth_file)
        instance['no_token'] = True
        instance['use_openmetrics'] = use_openmetrics
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(Exception, match='400 Client Error: Bad Request for url'):
            dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)

        if use_openmetrics:
            tags = global_tags + ['endpoint:{}/sys/metrics?format=prometheus'.format(instance['api_url'])]
            aggregator.assert_service_check('vault.openmetrics.health', status=c.CRITICAL, count=1, tags=tags)
        else:
            aggregator.assert_service_check(
                Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=1, tags=global_tags
            )

    @noauth_required
    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_noauth_needed(self, aggregator, dd_run_check, no_token_instance, global_tags, use_openmetrics):
        no_token_instance['use_openmetrics'] = use_openmetrics
        c = Vault(Vault.CHECK_NAME, {}, [no_token_instance])
        dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)

        if use_openmetrics:
            aggregator.assert_service_check('vault.openmetrics.health', status=c.CRITICAL, count=0)

    def test_route_transform(self, aggregator, no_token_instance, global_tags, mock_http_response):
        no_token_instance['use_openmetrics'] = False
        c = Vault(Vault.CHECK_NAME, {}, [no_token_instance])

        c.parse_config()

        mock_http_response(file_path=get_fixture_path('route_transform_metrics.txt'))

        c.process(c._scraper_config, c._metric_transformers)

        for quantile in [0.5, 0.9, 0.99]:
            quantile_tag = 'quantile:{}'.format(quantile)
            aggregator.assert_metric('vault.vault.route.rollback.sys.quantile', tags=global_tags + [quantile_tag])
            aggregator.assert_metric(
                'vault.route.rollback.quantile', tags=global_tags + [quantile_tag, 'mountpoint:sys']
            )
            aggregator.assert_metric(
                'vault.route.rollback.quantile', tags=global_tags + [quantile_tag, 'mountpoint:sys']
            )
            aggregator.assert_metric(
                'vault.route.create.quantile', tags=global_tags + [quantile_tag, 'mountpoint:foobar']
            )

        aggregator.assert_metric('vault.vault.route.rollback.sys.sum', tags=global_tags)
        aggregator.assert_metric('vault.vault.route.rollback.sys.count', tags=global_tags)
        aggregator.assert_metric('vault.route.rollback.sum', tags=global_tags + ['mountpoint:sys'])
        aggregator.assert_metric('vault.route.rollback.count', tags=global_tags + ['mountpoint:sys'])
        aggregator.assert_metric('vault.route.create.sum', tags=global_tags + ['mountpoint:foobar'])
        aggregator.assert_metric('vault.route.create.count', tags=global_tags + ['mountpoint:foobar'])

        aggregator.assert_all_metrics_covered()
        aggregator.assert_no_duplicate_metrics()

    def test_wal_merkle_metrics(self, aggregator, instance, dd_run_check, global_tags, mock_http_response):
        instance = instance()
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        c.parse_config()
        mock_http_response(file_path=get_fixture_path('merkle_wal_metrics.txt'))

        c.process(c._scraper_config, c._metric_transformers)

        for metric in MERKLE_WAL_METRICS:
            if metric in MERKLE_WAL_QUANTILES:
                for quantile in [0.5, 0.9, 0.99]:
                    quantile_tag = 'quantile:{}'.format(quantile)
                    aggregator.assert_metric('{}.quantile'.format(metric), tags=global_tags + [quantile_tag])
            aggregator.assert_metric('{}.sum'.format(metric), tags=global_tags)
            aggregator.assert_metric('{}.count'.format(metric), tags=global_tags)

        aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_x_vault_request_header_is_set(monkeypatch, instance, dd_run_check, use_openmetrics):
    instance = instance()
    instance['use_openmetrics'] = use_openmetrics

    c = Vault(Vault.CHECK_NAME, {}, [instance])

    requests_get = requests.get
    mock_get = mock.Mock(side_effect=requests_get)
    monkeypatch.setattr(requests, 'get', mock_get)

    dd_run_check(c)

    assert mock_get.call_count > 0
    for call in mock_get.call_args_list:
        headers = dict(call.kwargs['headers'])
        assert 'X-Vault-Request' in headers
        assert headers['X-Vault-Request'] == 'true'
