# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from decimal import Decimal
from typing import Any, Callable, Dict  # noqa: F401

import mock

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.utils.db import Query
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.snowflake import SnowflakeCheck, queries

from .common import CHECK_NAME, EXPECTED_TAGS


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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_currency_usage(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_currency_metrics = [
        ('test', 'Standard', 'Compute', 'USD', Decimal('0.4'), Decimal('0.7')),
    ]
    expected_tags = EXPECTED_TAGS + [
        'billing_account:test',
        'service_level:Standard',
        'usage_type:Compute',
        'currency:USD',
    ]
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_currency_metrics
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgCurrencyUsage)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.organization.currency.usage', value=0.4, tags=expected_tags)
    aggregator.assert_metric(
        'snowflake.organization.currency.usage_in_currency', value=0.7, count=1, tags=expected_tags
    )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_org_credit_usage(dd_run_check, aggregator, instance):
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
    aggregator.assert_metric('snowflake.organization.credit.virtual_warehouse.sum', value=300, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.credit.virtual_warehouse.avg', value=3.4, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.credit.cloud_service.sum', value=902.49003, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.credit.cloud_service.avg', value=4.9227, tags=expected_tags)
    aggregator.assert_metric(
        'snowflake.organization.credit.cloud_service_adjustment.sum', value=212.43, tags=expected_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.cloud_service_adjustment.avg', value=34.7, tags=expected_tags
    )
    aggregator.assert_metric('snowflake.organization.credit.total_credit.sum', value=342.8321, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.credit.total_credit.avg', value=1.7, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.credit.total_credits_billed.sum', value=21.02, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.credit.total_credits_billed.avg', value=2.9, tags=expected_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_org_contract_items(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_org_contract_metrics = [
        (
            Decimal('4'),
            'Free Usage',
            'USD',
            Decimal('23'),
        ),
    ]
    expected_tags = EXPECTED_TAGS + [
        'contract_number:4',
        'contract_item:Free Usage',
        'currency:USD',
    ]
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_org_contract_metrics
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgContractItems)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.organization.contract.amount', value=23, tags=expected_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_org_warehouse_credit_usage(dd_run_check, aggregator, instance):
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
    aggregator.assert_metric('snowflake.organization.warehouse.virtual_warehouse.sum', value=300, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.warehouse.virtual_warehouse.avg', value=3.4, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.warehouse.cloud_service.sum', value=902.49003, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.warehouse.cloud_service.avg', value=4.9227, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.warehouse.total_credit.sum', value=212.43, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.warehouse.total_credit.avg', value=34.7, tags=expected_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_org_storage_daily(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_storage_daily_metrics = [
        (
            'account_name',
            Decimal('4510'),
            Decimal('349'),
        ),
    ]
    expected_tags = EXPECTED_TAGS + [
        'billing_account:account_name',
    ]
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_storage_daily_metrics
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgStorageDaily)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.organization.storage.average_bytes', value=4510, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.storage.credits', value=349, tags=expected_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_org_balance(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_balance_metrics = [
        (
            Decimal('3'),
            'USD',
            Decimal('23410'),
            Decimal('814349'),
            Decimal('-35435'),
            Decimal('455435'),
        ),
    ]
    expected_tags = EXPECTED_TAGS + ['contract_number:3', 'currency:USD']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_balance_metrics):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgBalance)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.organization.balance.free_usage', value=23410, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.balance.capacity', value=814349, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.balance.on_demand_consumption', value=-35435, tags=expected_tags)
    aggregator.assert_metric('snowflake.organization.balance.rollover', value=455435, tags=expected_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_org_data_transfer(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_data_transfer_metrics = [
        (
            'test_account',
            'AWS',
            'GCP',
            'COPY',
            Decimal('13.56'),
        ),
    ]
    expected_tags = EXPECTED_TAGS + [
        'billing_account:test_account',
        'source_cloud:AWS',
        'target_cloud:GCP',
        'transfer_type:COPY',
    ]
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_data_transfer_metrics
    ):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgDataTransfer)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.organization.data_transfer.bytes_transferred', value=13.56, tags=expected_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_org_rate_sheet(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_rate_metrics = [
        (
            Decimal('3'),
            'test_account',
            'usage',
            'service',
            'USD',
            Decimal('312'),
        ),
    ]
    expected_tags = EXPECTED_TAGS + [
        'contract_number:3',
        'billing_account:test_account',
        'usage_type:usage',
        'service_type:service',
        'currency:USD',
    ]
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_rate_metrics):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.OrgRateSheet)]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.organization.rate.effective_rate', value=312, tags=expected_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()
