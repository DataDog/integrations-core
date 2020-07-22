# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any, Dict

import mock
from decimal import *
import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.snowflake import SnowflakeCheck


def test_storage_metrics(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = SnowflakeCheck('snowflake', {}, [instance])

    expected_storage_metrics = [(Decimal('0.000000'), Decimal('2520.000000'), Decimal('0.000000'))]

    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_storage_metrics):
        dd_run_check(check)

    aggregator.assert_metric('snowflake.storage.storage_bytes')
    aggregator.assert_metric('snowflake.storage.stage_bytes')
    aggregator.assert_metric('snowflake.storage.failsafe_bytes')

    aggregator.assert_all_metrics_covered()
