# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.rethinkdb import RethinkDBCheck

from .common import E2E_METRICS


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    # type: (Callable) -> None
    aggregator = dd_agent_check(rate=True)  # type: AggregatorStub

    for metric, _ in E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK)
