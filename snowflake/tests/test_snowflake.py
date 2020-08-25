# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from decimal import Decimal
from typing import Any, Dict

import mock

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.snowflake import SnowflakeCheck, queries

EXPECTED_TAGS = ['account:test_acct.us-central1.gcp']


def test_storage_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None

    expected_storage = [(Decimal('0.000000'), Decimal('1206.000000'), Decimal('19.200000'))]
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_storage):
        check = SnowflakeCheck('snowflake', {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [queries.StorageUsageMetrics]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.storage.storage_bytes.total', value=0.0, tags=EXPECTED_TAGS)
    aggregator.assert_metric('snowflake.storage.stage_bytes.total', value=1206.0, tags=EXPECTED_TAGS)
    aggregator.assert_metric('snowflake.storage.failsafe_bytes.total', value=19.2, tags=EXPECTED_TAGS)


def test_db_storage_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None

    expected_db_storage_usage = [('SNOWFLAKE_DB', Decimal('133.000000'), Decimal('9.100000'))]
    expected_tags = EXPECTED_TAGS + ['database:SNOWFLAKE_DB']
    with mock.patch(
        'datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_db_storage_usage
    ):
        check = SnowflakeCheck('snowflake', {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [queries.DatabaseStorageMetrics]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.storage.database.storage_bytes', value=133.0, tags=expected_tags)
    aggregator.assert_metric('snowflake.storage.database.failsafe_bytes', value=9.1, tags=expected_tags)


def test_credit_usage_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None

    expected_credit_usage = [
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0.218333333'), Decimal('0.000566111'), Decimal('0.218899444')),
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0.166666667'), Decimal('0.000270556'), Decimal('0.166937223')),
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0E-9'), Decimal('0.000014722'), Decimal('0.000014722')),
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0.183611111'), Decimal('0.000303333'), Decimal('0.183914444')),
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0.016666667'), Decimal('0E-9'), Decimal('0.016666667')),
    ]
    expected_tags = EXPECTED_TAGS + ['service_type:WAREHOUSE_METERING', 'service:COMPUTE_WH']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_credit_usage):
        check = SnowflakeCheck('snowflake', {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [queries.CreditUsage]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.billing.cloud_service', count=5, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.total', count=5)
    aggregator.assert_metric('snowflake.billing.virtual_warehouse', count=5)


def test_warehouse_usage_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None

    expected_wh_usage = [
        ('COMPUTE_WH', Decimal('0.286111111'), Decimal('0.002308056'), Decimal('0.288419167')),
        ('COMPUTE_WH', Decimal('0.459166667'), Decimal('0.001471667'), Decimal('0.460638333')),
    ]
    expected_tags = EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_wh_usage):
        check = SnowflakeCheck('snowflake', {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [queries.WarehouseCreditUsage]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.billing.warehouse.cloud_service', count=2, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.warehouse.total', count=2, tags=expected_tags)
    aggregator.assert_metric('snowflake.billing.warehouse.virtual_warehouse', count=2, tags=expected_tags)


def test_login_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None

    expected_login_metrics = [('SNOWFLAKE_UI', 2, 6, 8), ('PYTHON_DRIVER', 0, 148, 148)]
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_login_metrics):
        check = SnowflakeCheck('snowflake', {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [queries.LoginMetrics]
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
    # type: (AggregatorStub, Dict[str, Any]) -> None

    expected_wl_metrics = [
        ('COMPUTE_WH', Decimal('0.000446667'), Decimal('0E-9'), Decimal('0E-9'), Decimal('0E-9')),
        ('COMPUTE_WH', Decimal('0.002356667'), Decimal('0E-9'), Decimal('0E-9'), Decimal('0E-9')),
    ]
    expected_tags = EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_wl_metrics):
        check = SnowflakeCheck('snowflake', {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [queries.WarehouseLoad]
        dd_run_check(check)
    aggregator.assert_metric('snowflake.query.executed', value=0.000446667, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.executed', value=0.002356667, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.queued_overload', value=0, count=2, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.queued_provision', value=0, count=2, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.blocked', value=0, count=2, tags=expected_tags)


def test_query_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None

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
        ),
    ]

    expected_tags = EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_query_metrics):
        check = SnowflakeCheck('snowflake', {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [queries.QueryHistory]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.query.execution_time', value=4.333333, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.compilation_time', value=24.555556, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_scanned', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_written', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_deleted', value=0, count=1, tags=expected_tags)
