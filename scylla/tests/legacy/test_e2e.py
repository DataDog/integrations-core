# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.scylla import ScyllaCheck
from tests.common import FLAKY_METRICS, INSTANCE_DEFAULT_METRICS


def test_check_ok(dd_agent_check, instance_legacy):
    aggregator = dd_agent_check(instance_legacy, rate=True)

    for metric in INSTANCE_DEFAULT_METRICS:
        if metric in FLAKY_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', ScyllaCheck.OK)
