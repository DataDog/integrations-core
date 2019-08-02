# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .common import INSTANCE, ALL_UNIT_METRICS, SOCKET_METRICS, UNIT_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE)

    # TODO: Add SERVICE_METRICS
    for metric in UNIT_METRICS + SOCKET_METRICS + ALL_UNIT_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
