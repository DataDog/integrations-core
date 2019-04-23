# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

from datadog_checks.kube_metrics_server import KubeMetricsServerCheck

instance = {
    'prometheus_url': 'https://localhost:443/metrics',
    'send_histograms_buckets': True,
    'health_service_check': True,
}

# Constants
CHECK_NAME = 'kube_metrics_server'
NAMESPACE = 'kube_metrics_server'


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


def test_check_metrics(aggregator, mock_metrics):
    c = KubeMetricsServerCheck(CHECK_NAME, None, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.authenticated_user.requests', value=141.0, tags=['username:other'])
    assert_metric('.kubelet_summary_scrapes_total', value=17.0, tags=['success:false'])
    assert_metric('.process.cpu_seconds_total', value=1.61, tags=[])
    assert_metric('.manager_tick_duration.sum', value=40.568365077999985, tags=[])
    assert_metric('.manager_tick_duration.count', value=17.0, tags=[])
    assert_metric('.scraper_duration.sum', value=0.000137543, tags=['source:kubelet_summary:ci-host'])
    assert_metric('.scraper_duration.count', value=17.0, tags=['source:kubelet_summary:ci-host'])
    assert_metric('.kubelet_summary_request_duration.sum', value=1.5491e-05, tags=['node:ci-host'])
    assert_metric('.kubelet_summary_request_duration.count', value=17, tags=['node:ci-host'])
    assert_metric('.scraper_last_time', value=1.555673692e09, tags=['source:kubelet_summary:ci-host'])
    assert_metric('.process.max_fds', value=1.048576e06, tags=[])
    assert_metric('.process.open_fds', value=10.0, tags=[])
    assert_metric('.process.resident_memory_bytes', value=3.3374208e07, tags=[])
    assert_metric('.process.start_time_seconds', value=1.55567267074e09, tags=[])
    assert_metric('.process.virtual_memory_bytes', value=4.9864704e07, tags=[])
    assert_metric('.go.gc_duration_seconds.sum', value=0.007900459, tags=[])
    assert_metric('.go.gc_duration_seconds.count', value=19.0, tags=[])
    assert_metric('.go.gc_duration_seconds.quantile')
    assert_metric('.go.goroutines', value=51.0, tags=[])
    assert_metric('.go.memstats.alloc_bytes', value=7.872808e06, tags=[])
    assert_metric('.go.memstats.alloc_bytes_total', value=4.871232e07, tags=[])
    assert_metric('.go.memstats.buck_hash_sys_bytes', value=1.469077e06, tags=[])
    assert_metric('.go.memstats.frees_total', value=346829.0, tags=[])
    assert_metric('.go.memstats.gc_sys_bytes', value=614400.0, tags=[])
    assert_metric('.go.memstats.heap_alloc_bytes', value=7.872808e06, tags=[])
    assert_metric('.go.memstats.heap_idle_bytes', value=1.286144e06, tags=[])
    assert_metric('.go.memstats.heap_inuse_bytes', value=1.0313728e07, tags=[])
    assert_metric('.go.memstats.heap_objects', value=51059.0, tags=[])
    assert_metric('.go.memstats.heap_released_bytes_total', value=1.130496e06, tags=[])
    assert_metric('.go.memstats.heap_sys_bytes', value=1.1599872e07, tags=[])
    assert_metric('.go.memstats.last_gc_time_seconds', value=1.5556736352033744e09, tags=[])
    assert_metric('.go.memstats.lookups_total', value=502.0, tags=[])
    assert_metric('.go.memstats.mallocs_total', value=397888.0, tags=[])
    assert_metric('.go.memstats.mcache_inuse_bytes', value=6944.0, tags=[])
    assert_metric('.go.memstats.mcache_sys_bytes', value=16384.0, tags=[])
    assert_metric('.go.memstats.mspan_inuse_bytes', value=136344.0, tags=[])
    assert_metric('.go.memstats.mspan_sys_bytes', value=147456.0, tags=[])
    assert_metric('.go.memstats.next_gc_bytes', value=1.161688e07, tags=[])
    assert_metric('.go.memstats.other_sys_bytes', value=1.171043e06, tags=[])
    assert_metric('.go.memstats.stack_inuse_bytes', value=983040.0, tags=[])
    assert_metric('.go.memstats.stack_sys_bytes', value=983040.0, tags=[])
    assert_metric('.go.memstats.sys_bytes', value=1.6001272e07, tags=[])
    aggregator.assert_service_check(NAMESPACE + ".prometheus.health")
    aggregator.assert_all_metrics_covered()
