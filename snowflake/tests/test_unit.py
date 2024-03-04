# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import os

import mock
import pytest

from datadog_checks.base import ensure_bytes
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
    no_token_config['username'] = "test_user"
    with pytest.raises(Exception, match='If using OAuth, you must specify a `token` or a `token_path`'):
        SnowflakeCheck(CHECK_NAME, {}, [no_token_config])

    oauth_inst = copy.deepcopy(oauth_instance)
    oauth_inst['authenticator'] = 'testauth'
    with pytest.raises(Exception, match='The Authenticator method set is invalid: testauth'):
        SnowflakeCheck(CHECK_NAME, {}, [oauth_inst])


def test_read_token(oauth_instance):
    oauth_token_path_inst = copy.deepcopy(oauth_instance)
    oauth_token_path_inst['token'] = None
    oauth_token_path_inst['token_path'] = os.path.join(os.path.dirname(__file__), 'keys', 'token')
    check = SnowflakeCheck(CHECK_NAME, {}, [oauth_token_path_inst])
    token = check.read_token()
    assert token == 'testtoken'
    check.check(oauth_instance)


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
            login_timeout=3,
            ocsp_response_cache_filename=None,
            authenticator='snowflake',
            token=None,
            private_key_file=None,
            private_key_file_pwd=None,
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
            login_timeout=3,
            ocsp_response_cache_filename=None,
            authenticator='oauth',
            token='testtoken',
            private_key_file=None,
            private_key_file_pwd=None,
            client_session_keep_alive=False,
            proxy_host=None,
            proxy_port=None,
            proxy_user=None,
            proxy_password=None,
        )


@pytest.mark.parametrize(
    'key_file, password',
    [
        pytest.param('rsa_key_example.p8', None, id='no password'),
        pytest.param('rsa_key_pass_example.p8', 'keypass', id='with password'),
    ],
)
def test_key_auth(dd_run_check, instance, key_file, password):
    # Key auth
    inst = copy.deepcopy(instance)
    inst['private_key_path'] = os.path.join(os.path.dirname(__file__), 'keys', key_file)
    inst['private_key_password'] = password

    with mock.patch('datadog_checks.snowflake.check.sf') as sf:
        check = SnowflakeCheck(CHECK_NAME, {}, [inst])
        dd_run_check(check)
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
            login_timeout=3,
            ocsp_response_cache_filename=None,
            authenticator='snowflake',
            token=None,
            private_key_file=inst['private_key_path'],
            private_key_file_pwd=ensure_bytes(inst['private_key_password']),
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
            login_timeout=3,
            ocsp_response_cache_filename=None,
            authenticator='snowflake',
            token=None,
            private_key_file=None,
            private_key_file_pwd=None,
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


def test_wrong_account_metric_groups(instance):
    instance = copy.deepcopy(instance)
    instance['metric_groups'] = [
        'snowflake.organization.warehouse',
        'snowflake.organization.currency',
        'snowflake.organization.storage',
    ]
    with pytest.raises(
        Exception,
        match='No valid metric_groups for `ACCOUNT_USAGE` or custom query configured, please list at least one.',
    ):
        SnowflakeCheck(CHECK_NAME, {}, [instance])


def test_wrong_org_metric_groups(instance):
    instance = copy.deepcopy(instance)
    instance['schema'] = 'ORGANIZATION_USAGE'
    instance['metric_groups'] = [
        'snowflake.logins',
    ]
    with pytest.raises(
        Exception,
        match='No valid metric_groups for `ORGANIZATION_USAGE` or custom query configured, please list at least one.',
    ):
        SnowflakeCheck(CHECK_NAME, {}, [instance])


def test_account_org_metric_groups(instance):
    instance = copy.deepcopy(instance)
    instance['metric_groups'] = [
        'snowflake.organization.warehouse',
        'snowflake.organization.currency',
        'snowflake.organization.storage',
        'snowflake.data_transfer',
    ]
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check._config.metric_groups == [
        'snowflake.organization.warehouse',
        'snowflake.organization.currency',
        'snowflake.organization.storage',
        'snowflake.data_transfer',
    ]

    assert check.metric_queries == [
        queries.DataTransferHistory,
    ]


def test_default_org_metric_groups(instance):
    instance = copy.deepcopy(instance)
    instance['schema'] = 'ORGANIZATION_USAGE'
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check._config.metric_groups == [
        'snowflake.organization.warehouse',
        'snowflake.organization.currency',
        'snowflake.organization.storage',
    ]

    assert check.metric_queries == [
        queries.OrgWarehouseCreditUsage,
        queries.OrgCurrencyUsage,
        queries.OrgStorageDaily,
    ]


def test_org_metric_groups(instance):
    instance = copy.deepcopy(instance)
    instance['schema'] = 'ORGANIZATION_USAGE'
    instance['metric_groups'] = ['snowflake.organization.currency', 'snowflake.organization.contracts']
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check._config.metric_groups == ['snowflake.organization.currency', 'snowflake.organization.contracts']

    assert check.metric_queries == [
        queries.OrgCurrencyUsage,
        queries.OrgContractItems,
    ]


def test_all_org_metric_groups(instance):
    instance = copy.deepcopy(instance)
    instance['schema'] = 'ORGANIZATION_USAGE'
    instance['metric_groups'] = [
        'snowflake.organization.contracts',
        'snowflake.organization.credit',
        'snowflake.organization.currency',
        'snowflake.organization.warehouse',
        'snowflake.organization.storage',
        'snowflake.organization.balance',
        'snowflake.organization.rate',
        'snowflake.organization.data_transfer',
    ]
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check._config.metric_groups == [
        'snowflake.organization.contracts',
        'snowflake.organization.credit',
        'snowflake.organization.currency',
        'snowflake.organization.warehouse',
        'snowflake.organization.storage',
        'snowflake.organization.balance',
        'snowflake.organization.rate',
        'snowflake.organization.data_transfer',
    ]

    assert check.metric_queries == [
        queries.OrgContractItems,
        queries.OrgCreditUsage,
        queries.OrgCurrencyUsage,
        queries.OrgWarehouseCreditUsage,
        queries.OrgStorageDaily,
        queries.OrgBalance,
        queries.OrgRateSheet,
        queries.OrgDataTransfer,
    ]


@pytest.mark.parametrize(
    'schema',
    [
        pytest.param('ACCOUNT_USAGE'),
        pytest.param('ORGANIZATION_USAGE'),
    ],
)
def test_no_valid_metric_groups(instance, schema):
    instance = copy.deepcopy(instance)
    instance['metric_groups'] = ['fake.metric.group']
    instance['schema'] = schema
    with pytest.raises(
        Exception,
        match='No valid metric_groups for `{}` or custom query configured, please list at least one.'.format(schema),
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check.log = mock.MagicMock()


@pytest.mark.parametrize(
    'schema',
    [
        pytest.param('ACCOUNT_USAGE'),
        pytest.param('ORGANIZATION_USAGE'),
    ],
)
def test_metric_group_exceptions(instance, schema, caplog):
    caplog.clear()
    caplog.set_level(logging.WARNING)
    instance = copy.deepcopy(instance)
    instance['metric_groups'] = ['fake.metric.group', 'snowflake.organization.warehouse', 'snowflake.logins']
    instance['schema'] = schema
    SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert (
        "Invalid metric_groups for `{}` found in snowflake conf.yaml: fake.metric.group".format(schema) in caplog.text
    )


def test_no_metric_group(instance):
    inst = copy.deepcopy(instance)
    inst['metric_groups'] = []
    with pytest.raises(
        Exception,
        match='No valid metric_groups for `ACCOUNT_USAGE` or custom query configured, please list at least one.',
    ):
        SnowflakeCheck(CHECK_NAME, {}, [inst])

    inst['custom_queries'] = [
        {
            'query': "SELECT a,b from mytable where a='stuff' limit 1;",
            'columns': [{}, {'name': 'metric.b', 'type': 'gauge'}],
        },
    ]
    SnowflakeCheck(CHECK_NAME, {}, [inst])


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
        'username': 'user',
        'password': 'password',
        'account': 'account',
        'role': 'role',
    }
    inst['aggregate_last_24_hours'] = aggregate_last_24_hours
    check = SnowflakeCheck(CHECK_NAME, {}, [inst])

    # Only one query configured
    assert check.metric_queries[0]['query'] == expected_query


def test_aggregate_last_24_hours_queries_multiple_instances():
    # This test checks that the `aggregate_last_24_hours` setting doesn't leak into other instances.
    inst_default = {
        'metric_groups': ['snowflake.replication'],
        'username': 'user',
        'password': 'password',
        'account': 'account',
        'role': 'role',
    }

    inst_last_24_hours = dict(inst_default)

    inst_default['aggregate_last_24_hours'] = False
    inst_last_24_hours['aggregate_last_24_hours'] = True

    check_default = SnowflakeCheck(CHECK_NAME, {}, [inst_default])
    check_last_24_hours = SnowflakeCheck(CHECK_NAME, {}, [inst_last_24_hours])

    assert check_default.metric_queries[0]['query'] == (
        'select database_name, avg(credits_used), sum(credits_used), '
        'avg(bytes_transferred), sum(bytes_transferred) from replication_usage_history '
        'where start_time >= date_trunc(day, current_date) group by 1;'
    )

    assert check_last_24_hours.metric_queries[0]['query'] == (
        'select database_name, avg(credits_used), sum(credits_used), '
        'avg(bytes_transferred), sum(bytes_transferred) from replication_usage_history '
        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1;'
    )
