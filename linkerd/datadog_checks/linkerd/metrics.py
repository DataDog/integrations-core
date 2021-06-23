# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRIC_MAP = {
    # V1 metrics
    'jvm:start_time': 'jvm.start_time',
    'jvm:thread:count': 'jvm.thread.count',
    'jvm:nonheap:committed': 'jvm.nonheap.committed',
    'jvm:nonheap:max': 'jvm.nonheap.max',
    'jvm:nonheap:used': 'jvm.nonheap.used',
    'jvm:gc:cycles': 'jvm.gc.cycles',
    'jvm:gc:msec': 'jvm.gc.msec',
    'jvm:heap:committed': 'jvm.heap.committed',
    'jvm:heap:max': 'jvm.heap.max',
    'jvm:heap:used': 'jvm.heap.used',
    'jvm:uptime': 'jvm.uptime',
    'jvm:num_cpus': 'jvm.num_cpus',
    'jvm:gc:ParNew:cycles': 'jvm.gc.ParNew.cycles',
    'jvm:gc:ConcurrentMarkSweep:cycles': 'jvm.gc.ConcurrentMarkSweep.cycles',
    'jvm:fd_count': 'jvm.fd_count',
    'jvm:gc:ConcurrentMarkSweep:msec': 'jvm.gc.ConcurrentMarkSweep.msec',
    'jvm:gc:ParNew:msec': 'jvm.gc.ParNew.msec',
    'jvm:mem:current:Par_Eden_Space:used': 'jvm.mem.current.Par_Eden_Space.used',
    'jvm:mem:current:Par_Survivor_Space:used': 'jvm.mem.current.Par_Survivor_Space.used',
    'jvm:mem:current:CMS_Old_Gen:used': 'jvm.mem.current.CMS_Old_Gen.used',
    'jvm:gc:eden:pause_msec': 'jvm.gc.eden.pause_msec',
    'rt:client:requests': 'rt.client.requests_s',
    'rt:client:success': 'rt.client.success_s',
    'rt:client:connections': 'rt.client.connections',
    'rt:client:connects': 'rt.client.connects_s',
    'rt:client:status:1XX': 'rt.client.status.1XX_s',
    'rt:client:status:2XX': 'rt.client.status.2XX_s',
    'rt:client:status:3XX': 'rt.client.status.3XX_s',
    'rt:client:status:4XX': 'rt.client.status.4XX_s',
    'rt:client:status:5XX': 'rt.client.status.5XX_s',
    'rt:client:pool_cached': 'rt.client.pool_cached',
    'rt:client:pool_num_too_many_waiters': 'rt.client.pool_num_too_many_waiters',
    'rt:client:pool_num_waited': 'rt.client.pool_num_waited',
    'rt:client:pool_size': 'rt.client.pool_size',
    'rt:client:pool_waiters': 'rt.client.pool_waiters',
    'rt:client:request_latency_ms': 'rt.client.request_latency_ms',
    'rt:server:connections': 'rt.server.connections',
    'rt:server:connects': 'rt.server.connects_s',
    'rt:server:request_latency_ms': 'rt.server.request_latency_ms',
    # V2 metrics
    'request_total': 'request_total',
    'response_latency_ms': 'response_latency',
    'response_total': 'response_total',
    'retry_skipped_total': 'retry_skipped_total',
    'route_request_total': 'route.request_total',
    'route_response_latency_ms': 'route.response_latency',
    'route_response_total': 'route.response_total',
    'route_retry_skipped_total': 'route.retry_skipped_total',
    'route_actual_request_total': 'route.actual_request_total',
    'route_actual_response_latency_ms': 'route.actual_response_latency',
    'route_actual_response_total': 'route.actual_response_total',
    'route_actual_retry_skipped_total': 'route.actual_retry_skipped_total',
    'tcp_open_total': 'tcp.open_total',
    'tcp_open_connections': 'tcp.open_connections',
    'tcp_read_bytes_total': 'tcp.read_bytes_total',
    'tcp_write_bytes_total': 'tcp.write_bytes_total',
    'tcp_close_total': 'tcp.close_total',
    'tcp_connection_duration_ms': 'tcp.connection_duration',
    'control_request_total': 'control.request_total',
    'control_response_latency_ms': 'control.response_latency',
    'control_response_total': 'control.response_total',
    'control_retry_skipped_total': 'control.retry_skipped_total',
    'process_start_time_seconds': 'process.start_time',
    'process_cpu_seconds_total': 'process.cpu_seconds_total',
    'process_open_fds': 'process.open_fds',
    'process_max_fds': 'process.max_fds',
    'process_virtual_memory_bytes': 'process.virtual_memory',
    'process_resident_memory_bytes': 'process.resident_memory',
}

TYPE_OVERRIDES = {
    'jvm:start_time': 'gauge',
    'jvm:thread:count': 'gauge',
    'jvm:nonheap:committed': 'gauge',
    'jvm:nonheap:max': 'gauge',
    'jvm:nonheap:used': 'gauge',
    'jvm:gc:cycles': 'gauge',
    'jvm:gc:msec': 'gauge',
    'jvm:heap:committed': 'gauge',
    'jvm:heap:max': 'gauge',
    'jvm:heap:used': 'gauge',
    'jvm:uptime': 'gauge',
    'jvm:num_cpus': 'gauge',
    'jvm:gc:ParNew:cycles': 'gauge',
    'jvm:gc:ConcurrentMarkSweep:cycles': 'gauge',
    'jvm:fd_count': 'gauge',
    'jvm:gc:ConcurrentMarkSweep:msec': 'gauge',
    'jvm:gc:ParNew:msec': 'gauge',
    'jvm:mem:current:Par_Eden_Space:used': 'gauge',
    'jvm:mem:current:Par_Survivor_Space:used': 'gauge',
    'jvm:mem:current:CMS_Old_Gen:used': 'gauge',
    'jvm:gc:eden:pause_msec': 'summary',
    'rt:client:requests': 'rate',
    'rt:client:success': 'rate',
    'rt:client:connections': 'gauge',
    'rt:client:connects': 'rate',
    'rt:client:status:1XX': 'rate',
    'rt:client:status:2XX': 'rate',
    'rt:client:status:3XX': 'rate',
    'rt:client:status:4XX': 'rate',
    'rt:client:status:5XX': 'rate',
    'rt:client:pool_cached': 'rate',
    'rt:client:pool_num_too_many_waiters': 'gauge',
    'rt:client:pool_num_waited': 'gauge',
    'rt:client:pool_size': 'gauge',
    'rt:client:pool_waiters': 'gauge',
    'rt:client:request_latency_ms': 'summary',
    'rt:server:connections': 'gauge',
    'rt:server:connects': 'rate',
    'rt:server:request_latency_ms': 'summary',
}


def construct_metrics_config(metric_map, type_overrides):
    metrics = []
    for raw_metric_name, metric_name in metric_map.items():
        if raw_metric_name.endswith('_total'):
            raw_metric_name = raw_metric_name[:-6]
            metric_name = metric_name[:-6]

        config = {raw_metric_name: {'name': metric_name}}
        if raw_metric_name in type_overrides:
            config[raw_metric_name]['type'] = type_overrides[raw_metric_name]

        metrics.append(config)

    return metrics
