# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import mock
import pytest
from requests.exceptions import HTTPError

from datadog_checks.base.utils.common import ensure_unicode
from datadog_checks.istio import Istio
from datadog_checks.istio.constants import MESH_NAMESPACE, MIXER_NAMESPACE

from .common import CITADEL_METRICS, GALLEY_METRICS, MESH_METRICS, MIXER_METRICS, NEW_MIXER_METRICS, PILOT_METRICS

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
    'grpc_io_server_completed_rpcs': 'grpc_io_server.completed_rpcs',
    'grpc_io_server_received_bytes_per_rpc': 'grpc_io_server.received_bytes_per_rpc',
    'grpc_io_server_sent_bytes_per_rpc': 'grpc_io_server.sent_bytes_per_rpc',
    'grpc_io_server_server_latency': 'grpc_io_server.server_latency',
    'mixer_config_attributes_total': 'config.attributes_total',
    'mixer_config_handler_configs_total': 'config.handler_configs_total',
    'mixer_config_instance_configs_total': 'config.instance_configs_total',
    'mixer_config_rule_configs_total': 'config.rule_configs_total',
    'mixer_dispatcher_destinations_per_request': 'dispatcher.destinations_per_request',
    'mixer_dispatcher_instances_per_request': 'dispatcher.instances_per_request',
    'mixer_handler_daemons_total': 'handler.daemons_total',
    'mixer_handler_new_handlers_total': 'handler.new_handlers_total',
    'mixer_mcp_sink_reconnections': 'mcp_sink.reconnections',
    'mixer_mcp_sink_request_acks_total': 'mcp_sink.request_acks_total',
    'mixer_runtime_dispatch_duration_seconds': 'runtime.dispatch_duration_seconds',
    'mixer_runtime_dispatches_total': 'runtime.dispatches_total',
}

MOCK_INSTANCE = {
    'istio_mesh_endpoint': 'http://localhost:42422/metrics',
    'mixer_endpoint': 'http://localhost:9093/metrics',
}


NEW_MOCK_INSTANCE = {
    'istio_mesh_endpoint': 'http://istio-telemetry:42422/metrics',
    'mixer_endpoint': 'http://istio-telemetry:15014/metrics',
    'pilot_endpoint': 'http://istio-pilot:15014/metrics',
    'galley_endpoint': 'http://istio-galley:15014/metrics',
    'citadel_endpoint': 'http://istio-citadel:15014/metrics',
}

NEW_MOCK_PILOT_ONLY_INSTANCE = {'pilot_endpoint': 'http://istio-pilot:15014/metrics'}

NEW_MOCK_GALLEY_ONLY_INSTANCE = {'galley_endpoint': 'http://istio-galley:15014/metrics'}


class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly returned by requests.get
    """

    def __init__(self, content, content_type, status=200):
        self.content = content if isinstance(content, list) else [content]
        self.headers = {'Content-Type': content_type}
        self.status = status
        self.encoding = 'utf-8'

    def iter_lines(self, **_):
        content = self.content.pop(0)
        for elt in content.split("\n"):
            yield ensure_unicode(elt)

    def raise_for_status(self):
        if self.status != 200:
            raise HTTPError('Not 200 Client Error')

    def close(self):
        pass


@pytest.fixture
def mesh_mixture_fixture():
    mesh_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'istio', 'mesh.txt')
    mixer_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'istio', 'mixer.txt')
    responses = []
    with open(mesh_file_path, 'r') as f:
        responses.append(f.read())
    with open(mixer_file_path, 'r') as f:
        responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_mesh_mixture_fixture():
    files = ['mesh.txt', 'mixer.txt', 'pilot.txt', 'galley.txt', 'citadel.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(os.path.dirname(__file__), 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_pilot_fixture():
    files = ['pilot.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(os.path.dirname(__file__), 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_galley_fixture():
    files = ['galley.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(os.path.dirname(__file__), 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


def test_istio(aggregator, mesh_mixture_fixture):
    """
    Test the full check
    """
    check = Istio('istio', {}, [MOCK_INSTANCE])
    check.check(MOCK_INSTANCE)

    for metric in MESH_METRICS + MIXER_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_new_istio(aggregator, new_mesh_mixture_fixture):
    check = Istio('istio', {},[NEW_MOCK_INSTANCE])
    check.check(NEW_MOCK_INSTANCE)

    for metric in MESH_METRICS + NEW_MIXER_METRICS + GALLEY_METRICS + PILOT_METRICS + CITADEL_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_pilot_only_istio(aggregator, new_pilot_fixture):
    check = Istio('istio', {}, [NEW_MOCK_PILOT_ONLY_INSTANCE])
    check.check(NEW_MOCK_PILOT_ONLY_INSTANCE)

    for metric in PILOT_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_galley_only_istio(aggregator, new_galley_fixture):
    check = Istio('istio', {}, [NEW_MOCK_GALLEY_ONLY_INSTANCE])
    check.check(NEW_MOCK_GALLEY_ONLY_INSTANCE)

    for metric in GALLEY_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_scraper_creator():
    check = Istio('istio', {}, [MOCK_INSTANCE])
    istio_mesh_config = check.config_map.get(MOCK_INSTANCE['istio_mesh_endpoint'])
    mixer_scraper_dict = check.config_map.get(MOCK_INSTANCE['mixer_endpoint'])

    assert istio_mesh_config['namespace'] == MESH_NAMESPACE
    assert mixer_scraper_dict['namespace'] == MIXER_NAMESPACE

    assert istio_mesh_config['metrics_mapper'] == MESH_METRICS_MAPPER
    assert mixer_scraper_dict['metrics_mapper'] == MESH_MIXER_MAPPER
