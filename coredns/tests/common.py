# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

CHECK_NAME = 'coredns'
NAMESPACE = 'coredns'

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
ATHOST = "@{}".format(HOST)
PORT = '9153'
URL = "http://{}:{}/metrics".format(HOST, PORT)

COREDNS_VERSION = [int(i) for i in os.environ['COREDNS_VERSION'].split(".")]

CONFIG_FILE = os.path.join(HERE, 'docker', 'coredns', 'Corefile-v1.%d' % COREDNS_VERSION[1])

COMMON_METRICS = [
    NAMESPACE + '.build_info',
    NAMESPACE + '.go.gc_duration_seconds.count',
    NAMESPACE + '.go.gc_duration_seconds.quantile',
    NAMESPACE + '.go.gc_duration_seconds.sum',
    NAMESPACE + '.go.goroutines',
    NAMESPACE + '.go.memstats.alloc_bytes',
    NAMESPACE + '.go.memstats.alloc_bytes_total',
    NAMESPACE + '.go.memstats.buck_hash_sys_bytes',
    NAMESPACE + '.go.memstats.frees_total',
    NAMESPACE + '.go.memstats.gc_sys_bytes',
    NAMESPACE + '.go.memstats.heap_alloc_bytes',
    NAMESPACE + '.go.memstats.heap_idle_bytes',
    NAMESPACE + '.go.memstats.heap_inuse_bytes',
    NAMESPACE + '.go.memstats.heap_objects',
    NAMESPACE + '.go.memstats.heap_sys_bytes',
    NAMESPACE + '.go.memstats.last_gc_time_seconds',
    NAMESPACE + '.go.memstats.lookups_total',
    NAMESPACE + '.go.memstats.mallocs_total',
    NAMESPACE + '.go.memstats.mcache_inuse_bytes',
    NAMESPACE + '.go.memstats.mcache_sys_bytes',
    NAMESPACE + '.go.memstats.mspan_inuse_bytes',
    NAMESPACE + '.go.memstats.mspan_sys_bytes',
    NAMESPACE + '.go.memstats.next_gc_bytes',
    NAMESPACE + '.go.memstats.other_sys_bytes',
    NAMESPACE + '.go.memstats.stack_inuse_bytes',
    NAMESPACE + '.go.memstats.stack_sys_bytes',
    NAMESPACE + '.go.memstats.sys_bytes',
    NAMESPACE + '.health_request_duration.count',
    NAMESPACE + '.health_request_duration.sum',
    NAMESPACE + '.panic_count.count',
    NAMESPACE + '.process.cpu_seconds_total',
    NAMESPACE + '.process.max_fds',
    NAMESPACE + '.process.open_fds',
    NAMESPACE + '.process.resident_memory_bytes',
    NAMESPACE + '.process.start_time_seconds',
    NAMESPACE + '.process.virtual_memory_bytes',
    NAMESPACE + '.request_count',
    NAMESPACE + '.cache_size.count',
    NAMESPACE + '.cache_misses_count',
    NAMESPACE + '.response_code_count',
    NAMESPACE + '.response_size.bytes.sum',
    NAMESPACE + '.response_size.bytes.count',
    NAMESPACE + '.request_size.bytes.sum',
    NAMESPACE + '.request_size.bytes.count',
    NAMESPACE + '.request_duration.seconds.sum',
    NAMESPACE + '.request_duration.seconds.count',
    NAMESPACE + '.forward_request_count',
    NAMESPACE + '.forward_request_duration.seconds.sum',
    NAMESPACE + '.forward_request_duration.seconds.count',
    NAMESPACE + '.forward_response_rcode_count',
]

COMMON_METRICS_OMV2 = [
    NAMESPACE + '.build_info',
    NAMESPACE + '.go.gc_duration_seconds.count',
    NAMESPACE + '.go.gc_duration_seconds.quantile',
    NAMESPACE + '.go.gc_duration_seconds.sum',
    NAMESPACE + '.go.goroutines',
    NAMESPACE + '.go.memstats.alloc_bytes',
    NAMESPACE + '.go.memstats.buck_hash_sys_bytes',
    NAMESPACE + '.go.memstats.frees_total.count',
    NAMESPACE + '.go.memstats.gc_sys_bytes',
    NAMESPACE + '.go.memstats.heap_alloc_bytes',
    NAMESPACE + '.go.memstats.heap_idle_bytes',
    NAMESPACE + '.go.memstats.heap_inuse_bytes',
    NAMESPACE + '.go.memstats.heap_objects',
    NAMESPACE + '.go.memstats.heap_sys_bytes',
    NAMESPACE + '.go.memstats.last_gc_time_seconds',
    NAMESPACE + '.go.memstats.lookups_total.count',
    NAMESPACE + '.go.memstats.mallocs_total.count',
    NAMESPACE + '.go.memstats.mcache_inuse_bytes',
    NAMESPACE + '.go.memstats.mcache_sys_bytes',
    NAMESPACE + '.go.memstats.mspan_inuse_bytes',
    NAMESPACE + '.go.memstats.mspan_sys_bytes',
    NAMESPACE + '.go.memstats.next_gc_bytes',
    NAMESPACE + '.go.memstats.other_sys_bytes',
    NAMESPACE + '.go.memstats.stack_inuse_bytes',
    NAMESPACE + '.go.memstats.stack_sys_bytes',
    NAMESPACE + '.go.memstats.sys_bytes',
    NAMESPACE + '.health_request_duration.count',
    NAMESPACE + '.health_request_duration.sum',
    NAMESPACE + '.health_request_duration.bucket',
    NAMESPACE + '.panic_count.count',
    NAMESPACE + '.process.cpu_seconds_total.count',
    NAMESPACE + '.process.max_fds',
    NAMESPACE + '.process.open_fds',
    NAMESPACE + '.process.resident_memory_bytes',
    NAMESPACE + '.process.start_time_seconds',
    NAMESPACE + '.process.virtual_memory_bytes',
    NAMESPACE + '.request_count.count',
    NAMESPACE + '.cache_size.count',
    NAMESPACE + '.cache_misses_count.count',
    NAMESPACE + '.response_code_count.count',
    NAMESPACE + '.response_size.bytes.sum',
    NAMESPACE + '.response_size.bytes.count',
    NAMESPACE + '.response_size.bytes.bucket',
    NAMESPACE + '.request_size.bytes.sum',
    NAMESPACE + '.request_size.bytes.count',
    NAMESPACE + '.request_size.bytes.bucket',
    NAMESPACE + '.request_duration.seconds.sum',
    NAMESPACE + '.request_duration.seconds.count',
    NAMESPACE + '.request_duration.seconds.bucket',
    NAMESPACE + '.forward_request_count.count',
    NAMESPACE + '.forward_request_duration.seconds.sum',
    NAMESPACE + '.forward_request_duration.seconds.count',
    NAMESPACE + '.forward_request_duration.seconds.bucket',
    NAMESPACE + '.forward_response_rcode_count.count',
]

METRICS_V1_2 = COMMON_METRICS + [
    # Has been removed from v1.7.0
    NAMESPACE + '.request_type_count',
    # The proxy plugin has been deprecated
    NAMESPACE + '.proxy_request_count',
    NAMESPACE + '.proxy_request_duration.seconds.sum',
    NAMESPACE + '.proxy_request_duration.seconds.count',
    NAMESPACE + '.forward_sockets_open',
]

METRICS_V1_2_OMV2 = COMMON_METRICS_OMV2 + [
    # Has been removed from v1.7.0
    NAMESPACE + '.request_type_count.count',
    NAMESPACE + '.proxy_request_count.count',
    NAMESPACE + '.proxy_request_duration.seconds.bucket',
    # The proxy plugin has been deprecated
    NAMESPACE + '.proxy_request_duration.seconds.sum',
    NAMESPACE + '.proxy_request_duration.seconds.count',
    NAMESPACE + '.forward_sockets_open',
    NAMESPACE + '.go.memstats.heap_released_bytes.count',
]

METRICS_V1_8 = COMMON_METRICS + [
    NAMESPACE + '.forward_max_concurrent_rejects',
    NAMESPACE + '.go.info',
    NAMESPACE + '.go.memstats.gc_cpu_fraction',
    NAMESPACE + '.go.memstats.heap_released_bytes',
    NAMESPACE + '.cache_request_count',
    NAMESPACE + '.plugin_enabled',
    NAMESPACE + '.forward_healthcheck_broken_count',
    NAMESPACE + '.hosts.reload_timestamp',
    NAMESPACE + '.reload.failed_count',
    NAMESPACE + '.health_request_failures_count',
]

METRICS_V1_8_OMV2 = COMMON_METRICS_OMV2 + [
    NAMESPACE + '.forward_max_concurrent_rejects.count',
    NAMESPACE + '.go.info',
    NAMESPACE + '.go.memstats.gc_cpu_fraction',
    NAMESPACE + '.go.memstats.heap_released_bytes',
    NAMESPACE + '.cache_request_count.count',
    NAMESPACE + '.plugin_enabled',
    NAMESPACE + '.forward_healthcheck_broken_count.count',
    NAMESPACE + '.hosts.reload_timestamp',
    NAMESPACE + '.reload.failed_count.count',
    NAMESPACE + '.health_request_failures_count.count',
]

METRICS_V1_14 = METRICS_V1_8 + [
    NAMESPACE + '.cache_evictions_count',
    NAMESPACE + '.forward_conn_cache_hits_count',
    NAMESPACE + '.forward_conn_cache_misses_count',
    NAMESPACE + '.dns64.requests_translated_count',
    NAMESPACE + '.https_response_code_count',
    NAMESPACE + '.acl.filtered_requests',
    NAMESPACE + '.acl.dropped_requests',
    NAMESPACE + '.quic_response_code_count',
    NAMESPACE + '.kubernetes.rest_client_request_duration.sum',
    NAMESPACE + '.kubernetes.rest_client_request_duration.count',
    NAMESPACE + '.kubernetes.rest_client_rate_limiter_duration.sum',
    NAMESPACE + '.kubernetes.rest_client_rate_limiter_duration.count',
    NAMESPACE + '.kubernetes.rest_client_requests_count',
    NAMESPACE + '.reload.version_info',
]

METRICS_V1_14_OMV2 = METRICS_V1_8_OMV2 + [
    NAMESPACE + '.cache_evictions_count.count',
    NAMESPACE + '.forward_conn_cache_hits_count.count',
    NAMESPACE + '.forward_conn_cache_misses_count.count',
    NAMESPACE + '.dns64.requests_translated_count.count',
    NAMESPACE + '.https_response_code_count.count',
    NAMESPACE + '.acl.filtered_requests.count',
    NAMESPACE + '.acl.dropped_requests.count',
    NAMESPACE + '.quic_response_code_count.count',
    NAMESPACE + '.kubernetes.rest_client_request_duration.sum',
    NAMESPACE + '.kubernetes.rest_client_request_duration.count',
    NAMESPACE + '.kubernetes.rest_client_request_duration.bucket',
    NAMESPACE + '.kubernetes.rest_client_rate_limiter_duration.sum',
    NAMESPACE + '.kubernetes.rest_client_rate_limiter_duration.count',
    NAMESPACE + '.kubernetes.rest_client_rate_limiter_duration.bucket',
    NAMESPACE + '.kubernetes.rest_client_requests_count.count',
    NAMESPACE + '.reload.version_info',
]


def _select_metrics(version):
    """Select the metrics to test based on the CoreDNS version."""
    if version[:2] == [1, 14]:
        return METRICS_V1_14
    if version[:2] == [1, 8]:
        return METRICS_V1_8
    return METRICS_V1_2


def _select_metrics_v2(version):
    """Select the v2 metrics to test based on the CoreDNS version."""
    if version[:2] == [1, 14]:
        return METRICS_V1_14_OMV2
    if version[:2] == [1, 8]:
        return METRICS_V1_8_OMV2
    return METRICS_V1_2_OMV2


METRICS = _select_metrics(COREDNS_VERSION)

METRICS_V2 = _select_metrics_v2(COREDNS_VERSION)
