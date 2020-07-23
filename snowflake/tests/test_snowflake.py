# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from decimal import Decimal
from typing import Any, Dict

import mock

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.snowflake import SnowflakeCheck


def test_storage_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = SnowflakeCheck('snowflake', {}, [instance])

    expected_data = [(Decimal('0.000000'), Decimal('2520.000000'), Decimal('0.000000'))]

    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_data):
        dd_run_check(check)

    aggregator.assert_metric('snowflake.storage.storage_bytes')
    aggregator.assert_metric('snowflake.storage.stage_bytes')
    aggregator.assert_metric('snowflake.storage.failsafe_bytes')


def test_billing_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = SnowflakeCheck('snowflake', {}, [instance])

    expected_data = [
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0.218333333'), Decimal('0.000566111'), Decimal('0.218899444')),
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0.166666667'), Decimal('0.000270556'), Decimal('0.166937223')),
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0E-9'), Decimal('0.000014722'), Decimal('0.000014722')),
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0.183611111'), Decimal('0.000303333'), Decimal('0.183914444')),
        ('WAREHOUSE_METERING', 'COMPUTE_WH', Decimal('0.016666667'), Decimal('0E-9'), Decimal('0.016666667')),
    ]

    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_data):
        dd_run_check(check)

    aggregator.assert_metric('snowflake.billing.cloud_service', count=5)
    aggregator.assert_metric('snowflake.billing.total', count=5)
    aggregator.assert_metric('snowflake.billing.virtual_warehouse', count=5)
