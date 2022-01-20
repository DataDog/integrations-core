# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest

from datadog_checks.snowflake import SnowflakeCheck, queries

from .common import CHECK_NAME, EXPECTED_TAGS

PROXY_CONFIG = {'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'}
INVALID_PROXY = {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}
INVALID_CONFIG = {
    "account": "test_acct.us-central1.gcp",
    "database": "SNOWFLAKE",
    "schema": "ACCOUNT_USAGE",
    'role': "ACCOUNTADMIN",
    "authenticator": "oauth",
}


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
    with pytest.raises(Exception, match='Must specify a user'):
        SnowflakeCheck(CHECK_NAME, {}, [account_config])


def test_default_authentication(instance):
    # Test default auth
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check._config.authenticator == 'snowflake'


def test_invalid_oauth(oauth_instance):
    # Test oauth without user
    with pytest.raises(Exception, match='Must specify a user'):
        SnowflakeCheck(CHECK_NAME, {}, [INVALID_CONFIG])

    # Test oauth without token
    no_token_config = copy.deepcopy(INVALID_CONFIG)
    no_token_config['user'] = "test_user"
    with pytest.raises(Exception, match='If using OAuth, you must specify a token'):
        SnowflakeCheck(CHECK_NAME, {}, [no_token_config])

    oauth_inst = copy.deepcopy(oauth_instance)
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
            proxy_host=None,
            proxy_port=None,
            proxy_user=None,
            proxy_password=None,
        )


def test_oauth_auth(oauth_instance):
    # Test oauth
    oauth_inst = copy.deepcopy(oauth_instance)

    with mock.patch('datadog_checks.snowflake.check.sf') as sf:
        check = SnowflakeCheck(CHECK_NAME, {}, [oauth_inst])
        check._conn = mock.MagicMock()
        check._query_manager = mock.MagicMock()
        check.check(oauth_inst)
        sf.connect.assert_called_with(
            user='testuser',
            password=None,
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
            proxy_host=None,
            proxy_port=None,
            proxy_user=None,
            proxy_password=None,
        )


def test_proxy_settings(instance):
    init_config = {
        'proxy_host': 'testhost',
        'proxy_port': 8000,
        'proxy_user': 'proxyuser',
        'proxy_password': 'proxypass',
    }

    with mock.patch('datadog_checks.snowflake.check.sf') as sf:
        check = SnowflakeCheck(CHECK_NAME, init_config, [instance])
        check._conn = mock.MagicMock()
        check._query_manager = mock.MagicMock()
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
            proxy_host='testhost',
            proxy_port=8000,
            proxy_user='proxyuser',
            proxy_password='proxypass',
        )


def test_default_metric_groups(instance):
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check._config.metric_groups == [
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
    assert check._config.metric_groups == ['snowflake.logins', 'snowflake.data_transfer']

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


def test_emit_generic_and_non_generic_tags_by_default(instance):
    instance = copy.deepcopy(instance)
    instance['disable_generic_tags'] = False
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    tags = EXPECTED_TAGS + ['service_type:WAREHOUSE_METERING', 'service:COMPUTE_WH']
    normalised_tags = tags + ['snowflake_service:COMPUTE_WH']
    assert set(normalised_tags) == set(check._normalize_tags_type(tags))


def test_emit_non_generic_tags_when_disabled(instance):
    instance = copy.deepcopy(instance)
    instance['disable_generic_tags'] = True
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    tags = EXPECTED_TAGS + ['service_type:WAREHOUSE_METERING', 'service:COMPUTE_WH']
    normalised_tags = EXPECTED_TAGS + ['service_type:WAREHOUSE_METERING', 'snowflake_service:COMPUTE_WH']
    assert set(normalised_tags) == set(check._normalize_tags_type(tags))


@pytest.mark.parametrize(
    'aggregate_last_24_hours, expected_query',
    [
        pytest.param(
            True,
            (
                'select database_name, avg(credits_used), sum(credits_used), '
                'avg(bytes_transferred), sum(bytes_transferred) from replication_usage_history '
                'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1;'
            ),
        ),
        pytest.param(
            False,
            (
                'select database_name, avg(credits_used), sum(credits_used), '
                'avg(bytes_transferred), sum(bytes_transferred) from replication_usage_history '
                'where start_time >= date_trunc(day, current_date) group by 1;'
            ),
        ),
    ],
)
def test_aggregate_last_24_hours_queries(aggregate_last_24_hours, expected_query):
    inst = {
        'metric_groups': ['snowflake.replication'],
        'user': 'user',
        'password': 'password',
        'account': 'account',
        'role': 'role',
    }
    inst['aggregate_last_24_hours'] = aggregate_last_24_hours
    check = SnowflakeCheck(CHECK_NAME, {}, [inst])

    # Only one query configured
    assert check.metric_queries[0]['query'] == expected_query
