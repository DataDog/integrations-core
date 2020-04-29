# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .metrics import FLAKY_METRICS, METRICS
from .utils import assert_service_checks_ok

pytestmark = [pytest.mark.e2e]


def test(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for m in sorted(aggregator._metrics.keys()):
        print("metric: ", m)

    assert_service_checks_ok(aggregator)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    for metric in FLAKY_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
