# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable  # noqa: F401

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.rethinkdb import RethinkDBCheck

from .common import CURRENT_ISSUES_METRICS, E2E_METRICS


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    # type: (Callable) -> None
    aggregator = dd_agent_check(rate=True)  # type: AggregatorStub

    for metric, _ in E2E_METRICS:
        aggregator.assert_metric(metric)
    for metric, _ in CURRENT_ISSUES_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK)
