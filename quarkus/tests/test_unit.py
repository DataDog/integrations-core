# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.quarkus import QuarkusCheck

EXPECTED_METRICS = [
    'http_server.requests.seconds.max',
    'http_server.active_requests',
    'http_server.bytes_read.max',
    'http_server.bytes_written.max',
    'http_server.connections.seconds.max',
    'jvm.buffer.count_buffers',
    'jvm.buffer.memory_used.bytes',
    'jvm.buffer.total_capacity.bytes',
    'jvm.classes.loaded_classes',
    'jvm.gc.live_data_size.bytes',
    'jvm.gc.max_data_size.bytes',
    'jvm.gc.overhead',
    'jvm.memory.committed.bytes',
    'jvm.memory.max.bytes',
    'jvm.memory.usage_after_gc',
    'jvm.memory.used.bytes',
    'jvm.threads.daemon_threads',
    'jvm.threads.live_threads',
    'jvm.threads.peak_threads',
    'jvm.threads.states_threads',
    'netty.allocator.memory.pinned',
    'netty.allocator.memory.used',
    'netty.allocator.pooled.arenas',
    'netty.allocator.pooled.cache_size',
    'netty.allocator.pooled.chunk_size',
    'netty.allocator.pooled.threadlocal_caches',
    'netty.eventexecutor.tasks_pending',
    'process.cpu.usage',
    'process.files.max_files',
    'process.files.open_files',
    'process.uptime.seconds',
    'system.cpu.count',
    'system.cpu.usage',
    'system.load_average_1m',
    'worker_pool.active',
    'worker_pool.idle',
    'worker_pool.queue.delay.seconds.max',
    'worker_pool.queue.size',
    'worker_pool.ratio',
    'worker_pool.usage.seconds.max',
]


EXPECTED_SUMMARIES = [
    'http_server.requests.seconds',
    'http_server.bytes_read',
    'http_server.bytes_written',
    'worker_pool.queue.delay.seconds',
    'worker_pool.usage.seconds',
]


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    # Given
    mock_http_response(file_path=Path(__file__).parent.absolute() / "fixtures" / "quarkus_auto_metrics.txt")
    check = QuarkusCheck('quarkus', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    for m in EXPECTED_METRICS:
        aggregator.assert_metric('quarkus.' + m)
    for sm in EXPECTED_SUMMARIES:
        aggregator.assert_metric('quarkus.' + sm + '.count')
        aggregator.assert_metric('quarkus.' + sm + '.sum')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance, mock_http_response):
    # Given
    mock_http_response(status_code=404)
    check = QuarkusCheck('quarkus', {}, [instance])
    # When
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)
    # Then
    aggregator.assert_service_check('quarkus.openmetrics.health', QuarkusCheck.CRITICAL)
