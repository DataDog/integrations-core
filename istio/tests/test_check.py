# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


import os

import mock
import pytest
from requests.exceptions import HTTPError

from datadog_checks.istio import Istio
from datadog_checks.utils.common import ensure_unicode

MESH_METRICS = [
    'istio.mesh.request.count',
    'istio.mesh.request.duration.count',
    'istio.mesh.request.duration.sum',
    'istio.mesh.request.size.count',
    'istio.mesh.request.size.sum',
    'istio.mesh.response.size.count',
    'istio.mesh.response.size.sum',
]


MIXER_METRICS = [
    'istio.mixer.adapter.dispatch_duration.count',
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
    'istio.mixer.process.virtual_memory_bytes',
]


NEW_MIXER_METRICS = [
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
    'istio.mixer.process.cpu_seconds_total',
    'istio.mixer.process.max_fds',
    'istio.mixer.process.open_fds',
    'istio.mixer.process.resident_memory_bytes',
    'istio.mixer.process.start_time_seconds',
    'istio.mixer.process.virtual_memory_bytes',
    'istio.mixer.grpc_io_server.completed_rpcs',
    'istio.mixer.grpc_io_server.received_bytes_per_rpc.count',
    'istio.mixer.grpc_io_server.received_bytes_per_rpc.sum',
    'istio.mixer.grpc_io_server.sent_bytes_per_rpc.count',
    'istio.mixer.grpc_io_server.sent_bytes_per_rpc.sum',
    'istio.mixer.grpc_io_server.server_latency.count',
    'istio.mixer.grpc_io_server.server_latency.sum',
    'istio.mixer.config.attributes_total',
    'istio.mixer.config.handler_configs_total',
    'istio.mixer.config.instance_configs_total',
    'istio.mixer.config.rule_configs_total',
    'istio.mixer.dispatcher.destinations_per_request.count',
    'istio.mixer.dispatcher.destinations_per_request.sum',
    'istio.mixer.dispatcher.instances_per_request.count',
    'istio.mixer.dispatcher.instances_per_request.sum',
    'istio.mixer.handler.daemons_total',
    'istio.mixer.handler.new_handlers_total',
    'istio.mixer.mcp_sink.reconnections',
    'istio.mixer.mcp_sink.request_acks_total',
    'istio.mixer.runtime.dispatches_total',
    'istio.mixer.runtime.dispatch_duration_seconds.count',
    'istio.mixer.runtime.dispatch_duration_seconds.sum',
]


PILOT_METRICS = [
    'istio.pilot.go.gc_duration_seconds.count',
    'istio.pilot.go.gc_duration_seconds.quantile',
    'istio.pilot.go.gc_duration_seconds.sum',
    'istio.pilot.go.goroutines',
    'istio.pilot.go.info',
    'istio.pilot.go.memstats.alloc_bytes',
    'istio.pilot.go.memstats.alloc_bytes_total',
    'istio.pilot.go.memstats.buck_hash_sys_bytes',
    'istio.pilot.go.memstats.frees_total',
    'istio.pilot.go.memstats.gc_cpu_fraction',
    'istio.pilot.go.memstats.gc_sys_bytes',
    'istio.pilot.go.memstats.heap_alloc_bytes',
    'istio.pilot.go.memstats.heap_idle_bytes',
    'istio.pilot.go.memstats.heap_inuse_bytes',
    'istio.pilot.go.memstats.heap_objects',
    'istio.pilot.go.memstats.heap_released_bytes',
    'istio.pilot.go.memstats.heap_sys_bytes',
    'istio.pilot.go.memstats.last_gc_time_seconds',
    'istio.pilot.go.memstats.lookups_total',
    'istio.pilot.go.memstats.mallocs_total',
    'istio.pilot.go.memstats.mcache_inuse_bytes',
    'istio.pilot.go.memstats.mcache_sys_bytes',
    'istio.pilot.go.memstats.mspan_inuse_bytes',
    'istio.pilot.go.memstats.mspan_sys_bytes',
    'istio.pilot.go.memstats.next_gc_bytes',
    'istio.pilot.go.memstats.other_sys_bytes',
    'istio.pilot.go.memstats.stack_inuse_bytes',
    'istio.pilot.go.memstats.stack_sys_bytes',
    'istio.pilot.go.memstats.sys_bytes',
    'istio.pilot.go.threads',
    'istio.pilot.process.cpu_seconds_total',
    'istio.pilot.process.max_fds',
    'istio.pilot.process.open_fds',
    'istio.pilot.process.resident_memory_bytes',
    'istio.pilot.process.start_time_seconds',
    'istio.pilot.process.virtual_memory_bytes',
    'istio.pilot.conflict.inbound_listener',
    'istio.pilot.conflict.outbound_listener.http_over_current_tcp',
    'istio.pilot.conflict.outbound_listener.tcp_over_current_http',
    'istio.pilot.conflict.outbound_listener.tcp_over_current_tcp',
    'istio.pilot.destrule_subsets',
    'istio.pilot.duplicate_envoy_clusters',
    'istio.pilot.eds_no_instances',
    'istio.pilot.endpoint_not_ready',
    'istio.pilot.invalid_out_listeners',
    'istio.pilot.mcp_sink.reconnections',
    'istio.pilot.mcp_sink.recv_failures_total',
    'istio.pilot.mcp_sink.request_acks_total',
    'istio.pilot.no_ip',
    'istio.pilot.proxy_convergence_time.count',
    'istio.pilot.proxy_convergence_time.sum',
    'istio.pilot.rds_expired_nonce',
    'istio.pilot.services',
    'istio.pilot.total_xds_internal_errors',
    'istio.pilot.total_xds_rejects',
    'istio.pilot.virt_services',
    'istio.pilot.vservice_dup_domain',
    'istio.pilot.xds',
    'istio.pilot.xds.eds_instances',
    'istio.pilot.xds.push.context_errors',
    'istio.pilot.xds.push.timeout',
    'istio.pilot.xds.push.timeout_failures',
    'istio.pilot.xds.pushes',
    'istio.pilot.xds.write_timeout',
]


GALLEY_METRICS = [
    'istio.galley.go.gc_duration_seconds.count',
    'istio.galley.go.gc_duration_seconds.quantile',
    'istio.galley.go.gc_duration_seconds.sum',
    'istio.galley.go.goroutines',
    'istio.galley.go.info',
    'istio.galley.go.memstats.alloc_bytes',
    'istio.galley.go.memstats.alloc_bytes_total',
    'istio.galley.go.memstats.buck_hash_sys_bytes',
    'istio.galley.go.memstats.frees_total',
    'istio.galley.go.memstats.gc_cpu_fraction',
    'istio.galley.go.memstats.gc_sys_bytes',
    'istio.galley.go.memstats.heap_alloc_bytes',
    'istio.galley.go.memstats.heap_idle_bytes',
    'istio.galley.go.memstats.heap_inuse_bytes',
    'istio.galley.go.memstats.heap_objects',
    'istio.galley.go.memstats.heap_released_bytes',
    'istio.galley.go.memstats.heap_sys_bytes',
    'istio.galley.go.memstats.last_gc_time_seconds',
    'istio.galley.go.memstats.lookups_total',
    'istio.galley.go.memstats.mallocs_total',
    'istio.galley.go.memstats.mcache_inuse_bytes',
    'istio.galley.go.memstats.mcache_sys_bytes',
    'istio.galley.go.memstats.mspan_inuse_bytes',
    'istio.galley.go.memstats.mspan_sys_bytes',
    'istio.galley.go.memstats.next_gc_bytes',
    'istio.galley.go.memstats.other_sys_bytes',
    'istio.galley.go.memstats.stack_inuse_bytes',
    'istio.galley.go.memstats.stack_sys_bytes',
    'istio.galley.go.memstats.sys_bytes',
    'istio.galley.go.threads',
    'istio.galley.process.cpu_seconds_total',
    'istio.galley.process.max_fds',
    'istio.galley.process.open_fds',
    'istio.galley.process.resident_memory_bytes',
    'istio.galley.process.start_time_seconds',
    'istio.galley.process.virtual_memory_bytes',
    'istio.galley.endpoint_no_pod',
    'istio.galley.mcp_source.clients_total',
    'istio.galley.mcp_source.message_size_bytes.count',
    'istio.galley.mcp_source.message_size_bytes.sum',
    'istio.galley.mcp_source.request_acks_total',
    'istio.galley.runtime_processor.event_span_duration_milliseconds.count',
    'istio.galley.runtime_processor.event_span_duration_milliseconds.sum',
    'istio.galley.runtime_processor.events_processed_total',
    'istio.galley.runtime_processor.snapshot_events_total.count',
    'istio.galley.runtime_processor.snapshot_events_total.sum',
    'istio.galley.runtime_processor.snapshot_lifetime_duration_milliseconds.count',
    'istio.galley.runtime_processor.snapshot_lifetime_duration_milliseconds.sum',
    'istio.galley.runtime_processor.snapshots_published_total',
    'istio.galley.runtime_state_type_instances_total',
    'istio.galley.runtime_strategy.on_change_total',
    'istio.galley.runtime_strategy.timer_max_time_reached_total',
    'istio.galley.runtime_strategy.quiesce_reached_total',
    'istio.galley.runtime_strategy.timer_resets_total',
    'istio.galley.source_kube.dynamic_converter_success_total',
    'istio.galley.source_kube.event_success_total',
    'istio.galley.validation.cert_key_updates',
    'istio.galley.validation.config_load',
    'istio.galley.validation.config_update',
    'istio.galley.validation.passed',
]


CITADEL_METRICS = [
    'istio.citadel.go.gc_duration_seconds.count',
    'istio.citadel.go.gc_duration_seconds.quantile',
    'istio.citadel.go.gc_duration_seconds.sum',
    'istio.citadel.go.goroutines',
    'istio.citadel.go.info',
    'istio.citadel.go.memstats.alloc_bytes',
    'istio.citadel.go.memstats.alloc_bytes_total',
    'istio.citadel.go.memstats.buck_hash_sys_bytes',
    'istio.citadel.go.memstats.frees_total',
    'istio.citadel.go.memstats.gc_cpu_fraction',
    'istio.citadel.go.memstats.gc_sys_bytes',
    'istio.citadel.go.memstats.heap_alloc_bytes',
    'istio.citadel.go.memstats.heap_idle_bytes',
    'istio.citadel.go.memstats.heap_inuse_bytes',
    'istio.citadel.go.memstats.heap_objects',
    'istio.citadel.go.memstats.heap_released_bytes',
    'istio.citadel.go.memstats.heap_sys_bytes',
    'istio.citadel.go.memstats.last_gc_time_seconds',
    'istio.citadel.go.memstats.lookups_total',
    'istio.citadel.go.memstats.mallocs_total',
    'istio.citadel.go.memstats.mcache_inuse_bytes',
    'istio.citadel.go.memstats.mcache_sys_bytes',
    'istio.citadel.go.memstats.mspan_inuse_bytes',
    'istio.citadel.go.memstats.mspan_sys_bytes',
    'istio.citadel.go.memstats.next_gc_bytes',
    'istio.citadel.go.memstats.other_sys_bytes',
    'istio.citadel.go.memstats.stack_inuse_bytes',
    'istio.citadel.go.memstats.stack_sys_bytes',
    'istio.citadel.go.memstats.sys_bytes',
    'istio.citadel.go.threads',
    'istio.citadel.process.cpu_seconds_total',
    'istio.citadel.process.max_fds',
    'istio.citadel.process.open_fds',
    'istio.citadel.process.resident_memory_bytes',
    'istio.citadel.process.start_time_seconds',
    'istio.citadel.process.virtual_memory_bytes',
    'istio.citadel.secret_controller.csr_err_count',
    'istio.citadel.secret_controller.secret_deleted_cert_count',
    'istio.citadel.secret_controller.svc_acc_created_cert_count',
    'istio.citadel.secret_controller.svc_acc_deleted_cert_count',
    'istio.citadel.server.authentication_failure_count',
    'istio.citadel.server.citadel_root_cert_expiry_timestamp',
    'istio.citadel.server.csr_count',
    'istio.citadel.server.csr_parsing_err_count',
    'istio.citadel.server.id_extraction_err_count',
    'istio.citadel.server.success_cert_issuance_count',
]


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
    check = Istio('istio', {}, {}, [MOCK_INSTANCE])
    check.check(MOCK_INSTANCE)

    for metric in MESH_METRICS + MIXER_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_new_istio(aggregator, new_mesh_mixture_fixture):
    check = Istio('istio', {}, {}, [NEW_MOCK_INSTANCE])
    check.check(NEW_MOCK_INSTANCE)

    for metric in MESH_METRICS + NEW_MIXER_METRICS + GALLEY_METRICS + PILOT_METRICS + CITADEL_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_pilot_only_istio(aggregator, new_pilot_fixture):
    check = Istio('istio', {}, {}, [NEW_MOCK_PILOT_ONLY_INSTANCE])
    check.check(NEW_MOCK_PILOT_ONLY_INSTANCE)

    for metric in PILOT_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_galley_only_istio(aggregator, new_galley_fixture):
    check = Istio('istio', {}, {}, [NEW_MOCK_GALLEY_ONLY_INSTANCE])
    check.check(NEW_MOCK_GALLEY_ONLY_INSTANCE)

    for metric in GALLEY_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_scraper_creator():
    check = Istio('istio', {}, {}, [MOCK_INSTANCE])
    istio_mesh_config = check.config_map.get(MOCK_INSTANCE['istio_mesh_endpoint'])
    mixer_scraper_dict = check.config_map.get(MOCK_INSTANCE['mixer_endpoint'])

    assert istio_mesh_config['namespace'] == Istio.MESH_NAMESPACE
    assert mixer_scraper_dict['namespace'] == Istio.MIXER_NAMESPACE

    assert istio_mesh_config['metrics_mapper'] == MESH_METRICS_MAPPER
    assert mixer_scraper_dict['metrics_mapper'] == MESH_MIXER_MAPPER
