# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from decimal import Decimal
from typing import Any, Callable, Dict

import mock

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.db import Query
from datadog_checks.snowflake import SnowflakeCheck, queries

from .common import CHECK_NAME, EXPECTED_TAGS


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance):
    config = copy.deepcopy(instance)
    config['login_timeout'] = 5
    check = SnowflakeCheck(CHECK_NAME, {}, [config])
    dd_run_check(check)
    aggregator.assert_service_check('snowflake.can_connect', SnowflakeCheck.CRITICAL)


def test_no_schema(dd_run_check, aggregator, instance):
    config = copy.deepcopy(instance)
    del config['schema']
    config['login_timeout'] = 5
    check = SnowflakeCheck(CHECK_NAME, {}, [config])
    dd_run_check(check)
    aggregator.assert_service_check('snowflake.can_connect', SnowflakeCheck.CRITICAL)


def test_storage_metrics(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_storage = [(Decimal('0.000000'), Decimal('1206.000000'), Decimal('19.200000'))]
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_storage):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.StorageUsageMetrics)]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.storage.storage_bytes.total', value=0.0, tags=EXPECTED_TAGS)
    aggregator.assert_metric('snowflake.storage.stage_bytes.total', value=1206.0, tags=EXPECTED_TAGS)
    aggregator.assert_metric('snowflake.storage.failsafe_bytes.total', value=19.2, tags=EXPECTED_TAGS)


def test_db_storage_metrics(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_db_storage_usage = [('SNOWFLAKE_DB', Decimal('133.000000'), Decimal('9.100000'))]
    expected_tags = EXPECTED_TAGS + ['database:SNOWFLAKE_DB']
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_db_storage_usage
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.DatabaseStorageMetrics)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.storage.database.storage_bytes', value=133.0, tags=expected_tags)
    aggregator.assert_metric('snowflake.storage.database.failsafe_bytes', value=9.1, tags=expected_tags)


def test_credit_usage_metrics(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_credit_usage = [
        (
            'WAREHOUSE_METERING',
            'COMPUTE_WH',
            Decimal('12.000000000'),
            Decimal('1.000000000'),
            Decimal('0.80397000'),
            Decimal('0.066997500000'),
            Decimal('12.803970000'),
            Decimal('1.066997500000'),
        )
    ]
    expected_tags = EXPECTED_TAGS + ['service_type:WAREHOUSE_METERING', 'snowflake_service:COMPUTE_WH']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_credit_usage):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.CreditUsage)]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.billing.cloud_service.sum', count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.cloud_service.avg', count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.total_credit.sum', count=1)
    aggregator.assert_metric('snowflake.billing.total_credit.avg', count=1)
    aggregator.assert_metric('snowflake.billing.virtual_warehouse.sum', count=1)
    aggregator.assert_metric('snowflake.billing.virtual_warehouse.avg', count=1)


def test_warehouse_usage_metrics(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_wh_usage = [
        (
            'COMPUTE_WH',
            Decimal('13.000000000'),
            Decimal('1.000000000'),
            Decimal('0.870148056'),
            Decimal('0.066934465846'),
            Decimal('13.870148056'),
            Decimal('1.066934465846'),
        )
    ]
    expected_tags = EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_wh_usage):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.WarehouseCreditUsage)]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.billing.warehouse.cloud_service.avg', count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.warehouse.total_credit.avg', count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.warehouse.virtual_warehouse.avg', count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.warehouse.cloud_service.sum', count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.warehouse.total_credit.sum', count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.warehouse.virtual_warehouse.sum', count=1, tags=expected_tags)


def test_login_metrics(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_login_metrics = [('SNOWFLAKE_UI', 2, 6, 8), ('PYTHON_DRIVER', 0, 148, 148)]
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_login_metrics):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.LoginMetrics)]
        dd_run_check(check)
    snowflake_tags = EXPECTED_TAGS + ['client_type:SNOWFLAKE_UI']
    aggregator.assert_metric('snowflake.logins.fail.count', value=2, tags=snowflake_tags)
    aggregator.assert_metric('snowflake.logins.success.count', value=6, tags=snowflake_tags)
    aggregator.assert_metric('snowflake.logins.total', value=8, tags=snowflake_tags)

    python_tags = EXPECTED_TAGS + ['client_type:PYTHON_DRIVER']
    aggregator.assert_metric('snowflake.logins.fail.count', value=0, tags=python_tags)
    aggregator.assert_metric('snowflake.logins.success.count', value=148, tags=python_tags)
    aggregator.assert_metric('snowflake.logins.total', value=148, tags=python_tags)


def test_warehouse_load(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_wl_metrics = [
        ('COMPUTE_WH', Decimal('0.000446667'), Decimal('0E-9'), Decimal('0E-9'), Decimal('0E-9')),
    ]
    expected_tags = EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_wl_metrics):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.WarehouseLoad)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.query.executed', value=0.000446667, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.queued_overload', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.queued_provision', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.blocked', value=0, count=1, tags=expected_tags)


def test_currency_usage(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_currency_metrics = [
        ('test', 'ORGANIZATION', 'Standard', Decimal('0.4'), Decimal('0.7')),
    ]
    expected_tags = EXPECTED_TAGS + [
        'billing_account:test',
        'organization_name:ORGANIZATION',
        'service_level:Standard',
    ]
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_currency_metrics
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgCurrencyUsage)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.contract.amount.avg', value=0.4, tags=expected_tags)
    aggregator.assert_metric('snowflake.contract.amount.sum', value=0.7, count=1, tags=expected_tags)


def test_organization_credit_usage(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_org_credit_usage_metrics = [
        (
            'account_name',
            'Standard',
            Decimal('300'),
            Decimal('3.4'),
            Decimal('902.49003'),
            Decimal('4.9227'),
            Decimal('212.43'),
            Decimal('34.7'),
            Decimal('342.8321'),
            Decimal('1.7'),
            Decimal('21.02'),
            Decimal('2.9'),
        ),
    ]
    expected_tags = EXPECTED_TAGS + [
        'billing_account:account_name',
        'service_type:Standard',
    ]
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_org_credit_usage_metrics
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgCreditUsage)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.organization.billing.compute.sum', value=300, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.billing.compute.avg', value=3.4, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.billing.cloud_service.sum', value=902.49003, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.billing.cloud_service.avg', value=4.9227, tags=expected_tags)
    aggregator.assert_metric(
        'snowflake.organization.billing.cloud_service_adjustment.sum', value=212.43, tags=expected_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.billing.cloud_service_adjustment.avg', value=34.7, tags=expected_tags
    )
    aggregator.assert_metric('snowflake.organization.billing.total_credit.sum', value=342.8321, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.billing.total_credit.avg', value=1.7, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.billing.total_credits_billed.sum', value=21.02, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.billing.total_credits_billed.avg', value=2.9, tags=expected_tags)


def test_warehouse_credit_usage(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_credit_usage_metrics = [
        (
            'test',
            'account_name',
            Decimal('300'),
            Decimal('3.4'),
            Decimal('902.49003'),
            Decimal('4.9227'),
            Decimal('212.43'),
            Decimal('34.7'),
        ),
    ]
    expected_tags = EXPECTED_TAGS + [
        'warehouse:test',
        'billing_account:account_name',
    ]
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_credit_usage_metrics
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgWarehouseCreditUsage)]
        dd_run_check(check)
    aggregator.assert_metric(
        'snowflake.organization.billing.warehouse.virtual_warehouse.sum', value=300, tags=expected_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.billing.warehouse.virtual_warehouse.avg', value=3.4, tags=expected_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.billing.warehouse.cloud_service.sum', value=902.49003, tags=expected_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.billing.warehouse.cloud_service.avg', value=4.9227, tags=expected_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.billing.warehouse.total_credit.sum', value=212.43, tags=expected_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.billing.warehouse.total_credit.avg', value=34.7, tags=expected_tags
    )


def test_token_path(dd_run_check, aggregator):
    instance = {
        'user': 'testuser',
        'account': 'account',
        'role': 'ACCOUNTADMIN',
        'authenticator': 'oauth',
        'token_path': '/path/to/token',
    }

    default_args = {
        'user': 'testuser',
        'password': None,
        'account': 'account',
        'database': 'SNOWFLAKE',
        'schema': 'ACCOUNT_USAGE',
        'warehouse': None,
        'role': 'ACCOUNTADMIN',
        'passcode_in_password': False,
        'passcode': None,
        'client_prefetch_threads': 4,
        'login_timeout': 60,
        'ocsp_response_cache_filename': None,
        'authenticator': 'oauth',
        'client_session_keep_alive': False,
        'private_key': None,
        'proxy_host': None,
        'proxy_port': None,
        'proxy_user': None,
        'proxy_password': None,
    }

    tokens = ['mytoken1', 'mytoken2', 'mytoken3']

    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    with mock.patch(
        'datadog_checks.snowflake.check.open',
        side_effect=[mock.mock_open(read_data=tok).return_value for tok in tokens],
    ), mock.patch('datadog_checks.snowflake.check.sf') as sf:
        dd_run_check(check)
        sf.connect.assert_called_once_with(token='mytoken1', **default_args)

        dd_run_check(check)
        sf.connect.assert_called_with(token='mytoken2', **default_args)

        dd_run_check(check)
        sf.connect.assert_called_with(token='mytoken3', **default_args)


def test_query_metrics(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_query_metrics = [
        (
            'USE',
            'COMPUTE_WH',
            'SNOWFLAKE',
            None,
            Decimal('4.333333'),
            Decimal('24.555556'),
            Decimal('0.000000'),
            Decimal('0.000000'),
            Decimal('0.000000'),
            Decimal('0.000000'),
            Decimal('0.000000'),
        ),
    ]

    expected_tags = EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_query_metrics):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.QueryHistory)]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.query.execution_time', value=4.333333, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.compilation_time', value=24.555556, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_scanned', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_written', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_deleted', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_spilled.local', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_spilled.remote', value=0, count=1, tags=expected_tags)


def test_version_metadata(dd_run_check, instance, datadog_agent):
    expected_version = [('4.30.2',)]
    version_metadata = {
        'version.major': '4',
        'version.minor': '30',
        'version.patch': '2',
        'version.raw': '4.30.2',
        'version.scheme': 'semver',
    }
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_version):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check.check_id = 'test:123'
        check._conn = mock.MagicMock()
        check._query_manager.queries = []
        dd_run_check(check)

    datadog_agent.assert_metadata('test:123', version_metadata)
