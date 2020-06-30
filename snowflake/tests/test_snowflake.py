# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.snowflake import SnowflakeCheck


def test_check(dd_run_check, aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = SnowflakeCheck('snowflake', {}, [instance])
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
