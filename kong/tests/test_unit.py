# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from six import PY2

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kong import Kong

from .common import HERE, METRICS_URL

pytestmark = [pytest.mark.unit, pytest.mark.skipif(PY2, reason='Test only available on Python 3')]

EXPECTED_METRICS = {
    'kong.bandwidth.count': 'monotonic_count',
    'kong.http.consumer.status.count': 'monotonic_count',
    'kong.http.status.count': 'monotonic_count',
    'kong.latency.bucket': 'monotonic_count',
    'kong.latency.count': 'monotonic_count',
    'kong.latency.sum': 'monotonic_count',
    'kong.memory.lua.shared_dict.bytes': 'gauge',
    'kong.memory.lua.shared_dict.total_bytes': 'gauge',
    'kong.memory.workers.lua.vms.bytes': 'gauge',
    'kong.nginx.http.current_connections': 'gauge',
    'kong.nginx.stream.current_connections': 'gauge',
    'kong.stream.status.count': 'monotonic_count',
}

EXPECTED_METRICS_v3 = {
    'kong.bandwidth.bytes.count': 'monotonic_count',
    'kong.http.requests.count': 'monotonic_count',
    'kong.kong.latency.ms.bucket': 'monotonic_count',
    'kong.kong.latency.ms.count': 'monotonic_count',
    'kong.kong.latency.ms.sum': 'monotonic_count',
    'kong.memory.lua.shared_dict.bytes': 'gauge',
    'kong.memory.lua.shared_dict.total_bytes': 'gauge',
    'kong.memory.workers.lua.vms.bytes': 'gauge',
    'kong.nginx.connections.total': 'gauge',
    'kong.nginx.requests.total': 'gauge',
    'kong.nginx.timers': 'gauge',
    'kong.request.latency.ms.bucket': 'monotonic_count',
    'kong.request.latency.ms.count': 'monotonic_count',
    'kong.request.latency.ms.sum': 'monotonic_count',
    'kong.upstream.latency.ms.bucket': 'monotonic_count',
    'kong.upstream.latency.ms.count': 'monotonic_count',
    'kong.upstream.latency.ms.sum': 'monotonic_count',
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def test_check_v3(aggregator, dd_run_check, mock_http_response):
    mock_http_response(file_path=get_fixture_path('prometheus-v3.txt'))
    instance = {
        'openmetrics_endpoint': METRICS_URL,
        'extra_metrics': [{'kong_memory_workers_lua_vms_bytes': 'memory.workers.lua.vms.bytes'}],
    }

    check = Kong('kong', {}, [instance])
    dd_run_check(check)

    for metric_name, metric_type in EXPECTED_METRICS_v3.items():
        aggregator.assert_metric(metric_name, metric_type=getattr(aggregator, metric_type.upper()))

    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        'kong.datastore.reachable', status=Kong.OK, tags=['endpoint:{}'.format(METRICS_URL)], count=1
    )


def test_check(aggregator, dd_run_check, mock_http_response):
    mock_http_response(file_path=get_fixture_path('prometheus.txt'))
    instance = {
        'openmetrics_endpoint': METRICS_URL,
        'extra_metrics': [{'kong_memory_workers_lua_vms_bytes': 'memory.workers.lua.vms.bytes'}],
    }
    check = Kong('kong', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check(
        'kong.openmetrics.health', status=Kong.OK, tags=['endpoint:{}'.format(METRICS_URL)], count=1
    )

    for metric_name, metric_type in EXPECTED_METRICS.items():
        aggregator.assert_metric(metric_name, metric_type=getattr(aggregator, metric_type.upper()))

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'kong.datastore.reachable', status=Kong.OK, tags=['endpoint:{}'.format(METRICS_URL)], count=1
    )

    assert len(aggregator.service_checks('kong.upstream.target.health')) == 3
    aggregator.assert_service_check(
        'kong.upstream.target.health',
        status=Kong.OK,
        tags=['address:localhost:1002', 'endpoint:{}'.format(METRICS_URL), 'target:target2', 'upstream:upstream2'],
        count=1,
    )
    aggregator.assert_service_check(
        'kong.upstream.target.health',
        status=Kong.CRITICAL,
        tags=['address:localhost:1003', 'endpoint:{}'.format(METRICS_URL), 'target:target3', 'upstream:upstream3'],
        count=1,
    )
    aggregator.assert_service_check(
        'kong.upstream.target.health',
        status=Kong.CRITICAL,
        tags=['address:localhost:1004', 'endpoint:{}'.format(METRICS_URL), 'target:target4', 'upstream:upstream4'],
        count=1,
    )
