
# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kuma import KumaCheck

import pytest
from pathlib import Path

EXPECTED_METRICS = [
    'api_server.http.requests_inflight',
    'certwatcher.read_certificate.errors_total',
    'certwatcher.read_certificate.total',
    'controller_runtime.active_workers',
    'controller_runtime.max_concurrent_reconciles',
    'controller_runtime.reconcile_errors_total',
    'controller_runtime.reconcile_panics_total',
    'controller_runtime.terminal_reconcile_errors_total',
    'go.goroutines',
    'go.threads',
    'leader.status',
    'leader_election.master_status',
    'process.cpu.seconds_total',
    'process.resident_memory.bytes',
    'process.virtual_memory.bytes',
    'process.virtual_memory.max_bytes',
]

EXPECTED_SUMMARIES = [
    'api_server.http.request_duration.seconds',
    'api_server.http.response_size.bytes',
    'controller_runtime.reconcile_time.seconds',
    'controller_runtime.webhook_latency.seconds',
    'controller_runtime.webhook_requests.total',
    'component.catalog_writer',
    'component.heartbeat',
    'component.hostname_generator',
    'component.ms_status_updater',
    'component.mzms_status_updater',
    'component.store_counter',
    'component.sub_finalizer',
    'component.vip_allocator',
    'component.zone_available_services',
    'store.operations',
]

def test_check(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=Path(__file__).parent.absolute() / "fixtures" / "metrics.txt")
    check = KumaCheck('kuma', {}, [instance])
    dd_run_check(check)
    for m in EXPECTED_METRICS:
        aggregator.assert_metric('kuma.' + m)
    for sm in EXPECTED_SUMMARIES:
        aggregator.assert_metric('kuma.' + sm + '.count')
        aggregator.assert_metric('kuma.' + sm + '.sum')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
