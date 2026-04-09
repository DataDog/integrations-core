# ABOUTME: End-to-end tests for the NiFi integration.
# ABOUTME: Runs the check via the Datadog Agent container against a real NiFi instance.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    # Connectivity (service check, not a metric)
    aggregator.assert_service_check('nifi.can_connect', AgentCheck.OK)

    # System diagnostics - JVM
    aggregator.assert_metric('nifi.system.jvm.daemon_threads')
    aggregator.assert_metric('nifi.system.jvm.heap_max')
    aggregator.assert_metric('nifi.system.jvm.heap_used')
    aggregator.assert_metric('nifi.system.jvm.heap_utilization')
    aggregator.assert_metric('nifi.system.jvm.non_heap_used')
    aggregator.assert_metric('nifi.system.jvm.total_threads')

    # System diagnostics - CPU
    aggregator.assert_metric('nifi.system.cpu.available_processors')
    aggregator.assert_metric('nifi.system.cpu.load_average')

    # System diagnostics - GC
    aggregator.assert_metric('nifi.system.gc.collection_count')
    aggregator.assert_metric('nifi.system.gc.collection_time')

    # System diagnostics - repositories
    aggregator.assert_metric('nifi.system.flowfile_repo.free_space')
    aggregator.assert_metric('nifi.system.flowfile_repo.used_space')
    aggregator.assert_metric('nifi.system.flowfile_repo.utilization')
    aggregator.assert_metric('nifi.system.content_repo.free_space')
    aggregator.assert_metric('nifi.system.content_repo.used_space')
    aggregator.assert_metric('nifi.system.content_repo.utilization')
    aggregator.assert_metric('nifi.system.provenance_repo.free_space')
    aggregator.assert_metric('nifi.system.provenance_repo.used_space')
    aggregator.assert_metric('nifi.system.provenance_repo.utilization')

    # Flow status
    aggregator.assert_metric('nifi.flow.active_threads')
    aggregator.assert_metric('nifi.flow.bytes_queued')
    aggregator.assert_metric('nifi.flow.disabled_count')
    aggregator.assert_metric('nifi.flow.flowfiles_queued')
    aggregator.assert_metric('nifi.flow.invalid_count')
    aggregator.assert_metric('nifi.flow.running_count')
    aggregator.assert_metric('nifi.flow.stopped_count')

    # Process groups
    aggregator.assert_metric('nifi.process_group.active_threads')
    aggregator.assert_metric('nifi.process_group.bytes_queued')
    aggregator.assert_metric('nifi.process_group.bytes_read')
    aggregator.assert_metric('nifi.process_group.bytes_written')
    aggregator.assert_metric('nifi.process_group.flowfiles_queued')
    aggregator.assert_metric('nifi.process_group.flowfiles_received')
    aggregator.assert_metric('nifi.process_group.flowfiles_sent')
    aggregator.assert_metric('nifi.process_group.flowfiles_transferred')

    # Connection metrics (enabled via E2E config)
    aggregator.assert_metric('nifi.connection.flowfiles_in')
    aggregator.assert_metric('nifi.connection.flowfiles_out')
    aggregator.assert_metric('nifi.connection.queued_bytes')
    aggregator.assert_metric('nifi.connection.queued_count')
    aggregator.assert_metric('nifi.connection.percent_use_bytes')
    aggregator.assert_metric('nifi.connection.percent_use_count')

    # Processor metrics (enabled via E2E config)
    aggregator.assert_metric('nifi.processor.active_threads')
    aggregator.assert_metric('nifi.processor.bytes_read')
    aggregator.assert_metric('nifi.processor.bytes_written')
    aggregator.assert_metric('nifi.processor.flowfiles_in')
    aggregator.assert_metric('nifi.processor.flowfiles_out')
    aggregator.assert_metric('nifi.processor.processing_nanos')
    aggregator.assert_metric('nifi.processor.run_status')
    aggregator.assert_metric('nifi.processor.task_count')

    # Cluster metrics (connected_node_count, total_node_count, is_healthy) are not tested here
    # because the Docker environment runs a single standalone NiFi node (clustered=false).
    # They are covered by unit tests in TestClusterHealth.

    aggregator.assert_all_metrics_covered()

    # Bulletin events may be present from the error-path flow (PutFile to /nonexistent).
    # Not asserted because bulletin timing depends on NiFi scheduling and check timing.
