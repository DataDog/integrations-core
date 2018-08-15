# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import mock
import os

# 3rd-party
import pytest

# project
from datadog_checks.istio import Istio
from datadog_checks.checks.prometheus import PrometheusScraper


MESH_METRICS = ['istio.mesh.request.count',
                'istio.mesh.request.duration.count',
                'istio.mesh.request.duration.sum',
                'istio.mesh.request.size.count',
                'istio.mesh.request.size.sum',
                'istio.mesh.response.size.count',
                'istio.mesh.response.size.sum']


MIXER_METRICS = ['istio.mixer.adapter.dispatch_duration.count',
                 'istio.mixer.adapter.dispatch_duration.sum',
                 'istio.mixer.go.gc_duration_seconds.count',
                 'istio.mixer.go.gc_duration_seconds.quantile',
                 'istio.mixer.go.gc_duration_seconds.sum',
                 'istio.mixer.go.goroutines',
                 'istio.mixer.go.info',
                 'istio.mixer.go.memstats.alloc_bytes',
                 'istio.mixer.go.memstats.alloc_bytes_total',
                 'istio.mixer.go.memstats.buck_hash_sys_bytes',
                 'istio.mixer.go.memstats.frees_total',
                 'istio.mixer.go.memstats.gc_cpu_fraction',
                 'istio.mixer.go.memstats.gc_sys_bytes',
                 'istio.mixer.go.memstats.heap_alloc_bytes',
                 'istio.mixer.go.memstats.heap_idle_bytes',
                 'istio.mixer.go.memstats.heap_inuse_bytes',
                 'istio.mixer.go.memstats.heap_objects',
                 'istio.mixer.go.memstats.heap_released_bytes',
                 'istio.mixer.go.memstats.heap_sys_bytes',
                 'istio.mixer.go.memstats.last_gc_time_seconds',
                 'istio.mixer.go.memstats.lookups_total',
                 'istio.mixer.go.memstats.mallocs_total',
                 'istio.mixer.go.memstats.mcache_inuse_bytes',
                 'istio.mixer.go.memstats.mcache_sys_bytes',
                 'istio.mixer.go.memstats.mspan_inuse_bytes',
                 'istio.mixer.go.memstats.mspan_sys_bytes',
                 'istio.mixer.go.memstats.next_gc_bytes',
                 'istio.mixer.go.memstats.other_sys_bytes',
                 'istio.mixer.go.memstats.stack_inuse_bytes',
                 'istio.mixer.go.memstats.stack_sys_bytes',
                 'istio.mixer.go.memstats.sys_bytes',
                 'istio.mixer.go.threads',
                 'istio.mixer.grpc.server.handled_total',
                 'istio.mixer.grpc.server.handling_seconds.count',
                 'istio.mixer.grpc.server.handling_seconds.sum',
                 'istio.mixer.grpc.server.msg_received_total',
                 'istio.mixer.grpc.server.msg_sent_total',
                 'istio.mixer.grpc.server.started_total',
                 'istio.mixer.adapter.dispatch_count',
                 'istio.mixer.adapter.old_dispatch_count',
                 'istio.mixer.adapter.old_dispatch_duration.count',
                 'istio.mixer.adapter.old_dispatch_duration.sum',
                 'istio.mixer.config.resolve_actions.count',
                 'istio.mixer.config.resolve_actions.sum',
                 'istio.mixer.config.resolve_count',
                 'istio.mixer.config.resolve_duration.count',
                 'istio.mixer.config.resolve_duration.sum',
                 'istio.mixer.config.resolve_rules.count',
                 'istio.mixer.config.resolve_rules.sum',
                 'istio.mixer.process.cpu_seconds_total',
                 'istio.mixer.process.max_fds',
                 'istio.mixer.process.open_fds',
                 'istio.mixer.process.resident_memory_bytes',
                 'istio.mixer.process.start_time_seconds',
                 'istio.mixer.process.virtual_memory_bytes']


MOCK_INSTANCE = {
    'istio_mesh_endpoint': 'http://localhost:42422/metrics',
    'mixer_endpoint': 'http://localhost:9093/metrics'
}


MESH_METRICS_MAPPER = {
    'istio_request_count': 'request.count',
    'istio_request_duration': 'request.duration',
    'istio_request_size': 'request.size',
    'istio_response_size': 'response.size',
    'istio_requests_total': 'request.count',
    'istio_request_duration_seconds': 'request.duration',
    'istio_request_bytes': 'request.size',
    'istio_response_bytes': 'response.size',
}


MESH_MIXER_MAPPER = {
    'go_gc_duration_seconds': 'go.gc_duration_seconds',
    'go_goroutines': 'go.goroutines',
    'go_info': 'go.info',
    'go_memstats_alloc_bytes': 'go.memstats.alloc_bytes',
    'go_memstats_alloc_bytes_total': 'go.memstats.alloc_bytes_total',
    'go_memstats_buck_hash_sys_bytes': 'go.memstats.buck_hash_sys_bytes',
    'go_memstats_frees_total': 'go.memstats.frees_total',
    'go_memstats_gc_cpu_fraction': 'go.memstats.gc_cpu_fraction',
    'go_memstats_gc_sys_bytes': 'go.memstats.gc_sys_bytes',
    'go_memstats_heap_alloc_bytes': 'go.memstats.heap_alloc_bytes',
    'go_memstats_heap_idle_bytes': 'go.memstats.heap_idle_bytes',
    'go_memstats_heap_inuse_bytes': 'go.memstats.heap_inuse_bytes',
    'go_memstats_heap_objects': 'go.memstats.heap_objects',
    'go_memstats_heap_released_bytes': 'go.memstats.heap_released_bytes',
    'go_memstats_heap_sys_bytes': 'go.memstats.heap_sys_bytes',
    'go_memstats_last_gc_time_seconds': 'go.memstats.last_gc_time_seconds',
    'go_memstats_lookups_total': 'go.memstats.lookups_total',
    'go_memstats_mallocs_total': 'go.memstats.mallocs_total',
    'go_memstats_mcache_inuse_bytes': 'go.memstats.mcache_inuse_bytes',
    'go_memstats_mcache_sys_bytes': 'go.memstats.mcache_sys_bytes',
    'go_memstats_mspan_inuse_bytes': 'go.memstats.mspan_inuse_bytes',
    'go_memstats_mspan_sys_bytes': 'go.memstats.mspan_sys_bytes',
    'go_memstats_next_gc_bytes': 'go.memstats.next_gc_bytes',
    'go_memstats_other_sys_bytes': 'go.memstats.other_sys_bytes',
    'go_memstats_stack_inuse_bytes': 'go.memstats.stack_inuse_bytes',
    'go_memstats_stack_sys_bytes': 'go.memstats.stack_sys_bytes',
    'go_memstats_sys_bytes': 'go.memstats.sys_bytes',
    'go_threads': 'go.threads',
    'grpc_server_handled_total': 'grpc.server.handled_total',
    'grpc_server_handling_seconds': 'grpc.server.handling_seconds',
    'grpc_server_msg_received_total': 'grpc.server.msg_received_total',
    'grpc_server_msg_sent_total': 'grpc.server.msg_sent_total',
    'grpc_server_started_total': 'grpc.server.started_total',
    'mixer_adapter_dispatch_count': 'adapter.dispatch_count',
    'mixer_adapter_dispatch_duration': 'adapter.dispatch_duration',
    'mixer_adapter_old_dispatch_count': 'adapter.old_dispatch_count',
    'mixer_adapter_old_dispatch_duration': 'adapter.old_dispatch_duration',
    'mixer_config_resolve_actions': 'config.resolve_actions',
    'mixer_config_resolve_count': 'config.resolve_count',
    'mixer_config_resolve_duration': 'config.resolve_duration',
    'mixer_config_resolve_rules': 'config.resolve_rules',
    'process_cpu_seconds_total': 'process.cpu_seconds_total',
    'process_max_fds': 'process.max_fds',
    'process_open_fds': 'process.open_fds',
    'process_resident_memory_bytes': 'process.resident_memory_bytes',
    'process_start_time_seconds': 'process.start_time_seconds',
    'process_virtual_memory_bytes': 'process.virtual_memory_bytes',
}


class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly returned by requests.get
    """

    def __init__(self, content, content_type):
        if isinstance(content, list):
            self.content = content
        else:
            self.content = [content]
        self.headers = {'Content-Type': content_type}

    def iter_lines(self, **_):
        content = self.content.pop(0)
        for elt in content.split("\n"):
            yield elt

    def close(self):
        pass


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def mesh_mixture_fixture():
    mesh_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'istio', 'mesh.txt')
    mixer_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'istio', 'mixer.txt')
    responses = []
    with open(mesh_file_path, 'rb') as f:
        responses.append(f.read())
    with open(mixer_file_path, 'rb') as f:
        responses.append(f.read())

    p = mock.patch('datadog_checks.checks.prometheus.PrometheusScraper.poll',
                   return_value=MockResponse(responses, 'text/plain'),
                   __name__="poll")
    yield p.start()
    p.stop()


def test_istio(aggregator, mesh_mixture_fixture):
    """
    Test the full check
    """
    c = Istio('istio', None, {}, [MOCK_INSTANCE])
    c.check(MOCK_INSTANCE)

    metrics = MESH_METRICS + MIXER_METRICS
    for metric in metrics:
        aggregator.assert_metric(metric)

    assert aggregator.metrics_asserted_pct == 100.0


def test_process_functions(aggregator, mesh_mixture_fixture):
    """
    Test the process functions, ensure that they process correctly
    """
    c = Istio('istio', None, {}, [MOCK_INSTANCE])
    c._process_istio_mesh(MOCK_INSTANCE)
    c._process_mixer(MOCK_INSTANCE)

    metrics = MESH_METRICS + MIXER_METRICS
    for metric in metrics:
        aggregator.assert_metric(metric)

    assert aggregator.metrics_asserted_pct == 100.0


def test_scraper_creator():
    c = Istio('istio', None, {}, [MOCK_INSTANCE])
    istio_mesh_scraper = c._get_istio_mesh_scraper(MOCK_INSTANCE)
    mixer_scraper = c._get_mixer_scraper(MOCK_INSTANCE)
    istio_mesh_scraper_dict = c._scrapers.get(MOCK_INSTANCE['istio_mesh_endpoint'])
    mixer_scraper_dict = c._scrapers.get(MOCK_INSTANCE['mixer_endpoint'])

    assert istio_mesh_scraper == istio_mesh_scraper_dict
    assert mixer_scraper == mixer_scraper_dict

    assert isinstance(istio_mesh_scraper, PrometheusScraper)
    assert isinstance(mixer_scraper, PrometheusScraper)

    assert istio_mesh_scraper.NAMESPACE == 'istio.mesh'
    assert mixer_scraper.NAMESPACE == 'istio.mixer'

    assert istio_mesh_scraper.metrics_mapper == MESH_METRICS_MAPPER
    assert mixer_scraper.metrics_mapper == MESH_MIXER_MAPPER
