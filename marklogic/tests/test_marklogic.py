# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.marklogic import MarklogicCheck

from .common import METRICS, INSTANCE


@pytest.mark.integration
# @pytest.mark.usefixtures("dd_environment")
def test_check(aggregator):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE])

    check.check(INSTANCE)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    # for metrics in aggregator._metrics.values():
    #     for m in metrics:
    #         print(m)
    #
    # 1/0


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

