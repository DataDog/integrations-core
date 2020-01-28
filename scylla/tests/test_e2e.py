# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.scylla import ScyllaCheck

from .common import INSTANCE_DEFAULT_METRICS


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for metric in INSTANCE_DEFAULT_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('scylla.prometheus.health', ScyllaCheck.OK)
