# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import HAZELCAST_VERSION
from .metrics import HAZELCAST_4_ONLY_METRICS, METRICS
from .utils import assert_service_checks_ok

pytestmark = [pytest.mark.e2e]


def test(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    assert_service_checks_ok(aggregator)

    expected_metrics = set(METRICS)
    if HAZELCAST_VERSION == "4.0.1":
        expected_metrics |= set(HAZELCAST_4_ONLY_METRICS)

    for metric in expected_metrics:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
