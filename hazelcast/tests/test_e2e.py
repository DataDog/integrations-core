# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .metrics import METRICS
from .utils import assert_service_checks_ok

pytestmark = [pytest.mark.e2e]


E2E_EXCLUDED_METRICS = {
    # these metrics are in the hazelcast docs but not available in the dev env
    "hazelcast.member.local_clock_time",
    "hazelcast.member.priority_frames_written",
    "hazelcast.member.migration_completed_count",
    "hazelcast.member.cluster_start_time",
    "hazelcast.member.closed_count",
    "hazelcast.member.priority_write_queue_size",
    "hazelcast.member.selector_recreate_count",
    "hazelcast.member.exception_count",
    "hazelcast.member.started_migrations",
    "hazelcast.member.bytes_received",
    "hazelcast.member.bytes_written",
    "hazelcast.member.in_progress_count",
    "hazelcast.member.normal_frames_read",
    "hazelcast.member.connection_listener_count",
    "hazelcast.member.normal_frames_written",
    "hazelcast.member.bytes_read",
    "hazelcast.member.idle_time_ms",
    "hazelcast.member.owner_id",
    "hazelcast.member.bytes_send",
    "hazelcast.member.opened_count",
    "hazelcast.member.scheduled",
    "hazelcast.member.priority_frames_read",
    "hazelcast.member.imbalance_detected_count",
}


def test(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    assert_service_checks_ok(aggregator)

    for metric in set(METRICS) - E2E_EXCLUDED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
