# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks

from .common import FRONTEND_METRICS_MOCK, WORKER_METRICS_MOCK


def test_check_dynamo_e2e(dd_agent_check, frontend_instance, worker_instance):
    aggregator = dd_agent_check({'instances': [frontend_instance, worker_instance]}, rate=True)

    # The unit tests exercise the aggregator stub; only the real Agent pipeline proves the
    # distribution path that get_default_config turns on (histogram_buckets_as_distributions and
    # collect_counters_with_distributions). Note this still only shows the check agrees with the
    # fixtures Caddy serves, not with a live Dynamo -- see the fixture provenance headers.
    for metric in FRONTEND_METRICS_MOCK + WORKER_METRICS_MOCK:
        aggregator.assert_metric(metric)

    aggregator.assert_service_check('dynamo.openmetrics.health', ServiceCheck.OK, count=4)
    assert_service_checks(aggregator)
