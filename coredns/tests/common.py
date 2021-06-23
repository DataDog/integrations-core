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


METRICS_V1_2 = COMMON_METRICS + [
    # Has been removed from v1.7.0
    NAMESPACE + '.request_type_count',
    # The proxy plugin has been deprecated
    NAMESPACE + '.proxy_request_count',
    NAMESPACE + '.proxy_request_duration.seconds.sum',
    NAMESPACE + '.proxy_request_duration.seconds.count',
    NAMESPACE + '.forward_sockets_open',
]

METRICS_V1_7 = COMMON_METRICS + [
    NAMESPACE + '.forward_max_concurrent_rejects',
    NAMESPACE + '.go.info',
    NAMESPACE + '.go.memstats.gc_cpu_fraction',
    NAMESPACE + '.go.memstats.heap_released_bytes',
    NAMESPACE + '.plugin_enabled',
]

METRICS = METRICS_V1_7 if COREDNS_VERSION[:2] == [1, 7] else METRICS_V1_2
