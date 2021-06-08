# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, Callable

import pytest
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.avi_vantage import AviVantageCheck


def test_check(aggregator, instance, dd_run_check):
    # type: (AggregatorStub, Dict[str, Any], Callable) -> None
    check = AviVantageCheck('avi_vantage', {}, [instance])
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
