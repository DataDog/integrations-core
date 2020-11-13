# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.snowflake import SnowflakeCheck, queries

from .conftest import CHECK_NAME

PROXY_CONFIG = {'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'}
INVALID_PROXY = {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}


def test_config():
    # Test missing account
    user_config = {
        'username': 'TestGuy',
        'password': 'badpass',
    }
    with pytest.raises(Exception, match='Must specify an account'):
        SnowflakeCheck(CHECK_NAME, {}, [user_config])

    # Test missing user and pass
    account_config = {'account': 'TEST123'}
    with pytest.raises(Exception, match='Must specify a user and password'):
        SnowflakeCheck(CHECK_NAME, {}, [account_config])


def test_default_authentication(instance):
    # Test default auth
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check.config.authenticator == 'snowflake'


def test_invalid_auth(instance):
    # Test oauth
    oauth_inst = copy.deepcopy(instance)
    oauth_inst['authenticator'] = 'oauth'
    with pytest.raises(Exception, match='If using OAuth, you must specify a token'):
        SnowflakeCheck(CHECK_NAME, {}, [oauth_inst])

    oauth_inst['authenticator'] = 'testauth'
    with pytest.raises(Exception, match='The Authenticator method set is invalid: testauth'):
        SnowflakeCheck(CHECK_NAME, {}, [oauth_inst])


def test_default_auth(instance):
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    check._conn = mock.MagicMock()
    check._query_manager = mock.MagicMock()

    with mock.patch('datadog_checks.snowflake.check.sf') as sf:
        check.check(instance)
        sf.connect.assert_called_with(
            user='testuser',
            password='pass',
            account='test_acct.us-central1.gcp',
            database='SNOWFLAKE',
            schema='ACCOUNT_USAGE',
            warehouse=None,
            role='ACCOUNTADMIN',
            passcode_in_password=False,
            passcode=None,
            client_prefetch_threads=4,
            login_timeout=60,
            ocsp_response_cache_filename=None,
            authenticator='snowflake',
            token=None,
            client_session_keep_alive=False,
        )


def test_oauth_auth(instance):
    # Test oauth
    oauth_inst = copy.deepcopy(instance)
    oauth_inst['authenticator'] = 'oauth'
    oauth_inst['token'] = 'testtoken'

    with mock.patch('datadog_checks.snowflake.check.sf') as sf:
        check = SnowflakeCheck(CHECK_NAME, {}, [oauth_inst])
        check._conn = mock.MagicMock()
        check._query_manager = mock.MagicMock()
        check.check(oauth_inst)
        sf.connect.assert_called_with(
            user='testuser',
            password='pass',
            account='test_acct.us-central1.gcp',
            database='SNOWFLAKE',
            schema='ACCOUNT_USAGE',
            warehouse=None,
            role='ACCOUNTADMIN',
            passcode_in_password=False,
            passcode=None,
            client_prefetch_threads=4,
            login_timeout=60,
            ocsp_response_cache_filename=None,
            authenticator='oauth',
            token='testtoken',
            client_session_keep_alive=False,
        )


def test_default_metric_groups(instance):
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check.config.metric_groups == [
        'snowflake.query',
        'snowflake.billing',
        'snowflake.storage',
        'snowflake.logins',
    ]

    assert check.metric_queries == [
        queries.WarehouseLoad,
        queries.QueryHistory,
        queries.CreditUsage,
        queries.WarehouseCreditUsage,
        queries.StorageUsageMetrics,
        queries.LoginMetrics,
    ]


def test_mixed_metric_group(instance):
    instance = copy.deepcopy(instance)
    instance['metric_groups'] = ['fake.metric.group', 'snowflake.logins']
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check.metric_queries == [queries.LoginMetrics]


def test_additional_metric_groups(instance):
    instance = copy.deepcopy(instance)
    instance['metric_groups'] = ['snowflake.logins', 'snowflake.data_transfer']
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check.config.metric_groups == ['snowflake.logins', 'snowflake.data_transfer']

    assert check.metric_queries == [
        queries.LoginMetrics,
        queries.DataTransferHistory,
    ]


def test_metric_group_exceptions(instance):
    instance = copy.deepcopy(instance)
    instance['metric_groups'] = ['fake.metric.group']
    with pytest.raises(Exception, match='No valid metric_groups configured, please list at least one.'):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check.log = mock.MagicMock()
        check.log.warning.assert_called_once_with(
            "Invalid metric_groups found in snowflake conf.yaml: fake.metric.group"
        )


def test_no_proxy_config():
    instance = {}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['proxies'] is None
    assert http.no_proxy_uris is None


def test_proxy_agent_config(instance):
    with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', return_value=PROXY_CONFIG):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])

        assert check.http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert check._proxies == {'http': 'http_host', 'https': 'https_host'}
        assert check.http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_proxy_init_config_override(instance):
    with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', return_value=INVALID_PROXY):
        init_config = {'proxy': PROXY_CONFIG}
        check = SnowflakeCheck(CHECK_NAME, init_config, [instance])
        assert check.http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert check._proxies == {'http': 'http_host', 'https': 'https_host'}
        assert check.http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_proxy_instance_override(instance):
    with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', return_value=INVALID_PROXY):
        instance = copy.deepcopy(instance)
        instance['proxy'] = PROXY_CONFIG
        init_config = {'proxy': INVALID_PROXY}
        check = SnowflakeCheck(CHECK_NAME, init_config, [instance])
        assert check.http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert check._proxies == {'http': 'http_host', 'https': 'https_host'}
        assert check.http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']
