# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib

# 3rd party

# project
from datadog_checks.checks.prometheus import PrometheusCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'linkerd'


class LinkerdCheck(PrometheusCheck):
    """
    Collect linkerd metrics from Prometheus
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(LinkerdCheck, self).__init__(name, init_config, agentConfig, instances)
        self.NAMESPACE = 'linkerd'

        self.metrics_mapper = {}
        self.type_overrides = {}

        metrics_map = {
            'jvm:start_time': 'jvm.start_time',
            'jvm:application_time_millis': 'jvm.application_time_millis',
            'jvm:classes:total_loaded': 'jvm.classes.total_loaded',
            'jvm:classes:current_loaded': 'jvm.classes.current_loaded',
            'jvm:classes:total_unloaded': 'jvm.classes.total_unloaded',
            'jvm:postGC:Par_Survivor_Space:max': 'jvm.postGC.Par_Survivor_Space.max',
            'jvm:postGC:Par_Survivor_Space:used': 'jvm.postGC.Par_Survivor_Space.used',
            'jvm:postGC:CMS_Old_Gen:max': 'jvm.postGC.CMS_Old_Gen.max',
            'jvm:postGC:CMS_Old_Gen:used': 'jvm.postGC.CMS_Old_Gen.used',
            'jvm:postGC:Par_Eden_Space:max': 'jvm.postGC.Par_Eden_Space.max',
            'jvm:postGC:Par_Eden_Space:used': 'jvm.postGC.Par_Eden_Space.used',
            'jvm:postGC:used': 'jvm.postGC.used',
            'jvm:nonheap:committed': 'jvm.nonheap.committed',
            'jvm:nonheap:max': 'jvm.nonheap.max',
            'jvm:nonheap:used': 'jvm.nonheap.used',
            'jvm:tenuring_threshold': 'jvm.tenuring_threshold',
            'jvm:thread:daemon_count': 'jvm.thread.daemon_count',
            'jvm:thread:count': 'jvm.thread.count',
            'jvm:thread:peak_count': 'jvm.thread.peak_count',
            'jvm:mem:postGC:Par_Survivor_Space:max': 'jvm.mem.postGC.Par_Survivor_Space.max',
            'jvm:mem:postGC:Par_Survivor_Space:used': 'jvm.mem.postGC.Par_Survivor_Space.used',
            'jvm:mem:postGC:CMS_Old_Gen:max': 'jvm.mem.postGC.CMS_Old_Gen.max',
            'jvm:mem:postGC:CMS_Old_Gen:used': 'jvm.mem.postGC.CMS_Old_Gen.used',
            'jvm:mem:postGC:Par_Eden_Space:max': 'jvm.mem.postGC.Par_Eden_Space.max',
            'jvm:mem:postGC:Par_Eden_Space:used': 'jvm.mem.postGC.Par_Eden_Space.used',
            'jvm:mem:postGC:used': 'jvm.mem.postGC.used',
            'jvm:mem:metaspace:max_capacity': 'jvm.mem.metaspace.max_capacity',
            'jvm:mem:buffer:direct:max': 'jvm.mem.buffer.direct.max',
            'jvm:mem:buffer:direct:count': 'jvm.mem.buffer.direct.count',
            'jvm:mem:buffer:direct:used': 'jvm.mem.buffer.direct.used',
            'jvm:mem:buffer:mapped:max': 'jvm.mem.buffer.mapped.max',
            'jvm:mem:buffer:mapped:count': 'jvm.mem.buffer.mapped.count',
            'jvm:mem:buffer:mapped:used': 'jvm.mem.buffer.mapped.used',
            'jvm:mem:allocations:eden:bytes': 'jvm.mem.allocations.eden.bytes',
            'jvm:mem:current:used': 'jvm.mem.current.used',
            'jvm:mem:current:CMS_Old_Gen:max': 'jvm.mem.current.CMS_Old_Gen.max',
            'jvm:mem:current:CMS_Old_Gen:used': 'jvm.mem.current.CMS_Old_Gen.used',
            'jvm:mem:current:Metaspace:max': 'jvm.mem.current.Metaspace.max',
            'jvm:mem:current:Metaspace:used': 'jvm.mem.current.Metaspace.used',
            'jvm:mem:current:Par_Eden_Space:max': 'jvm.mem.current.Par_Eden_Space.max',
            'jvm:mem:current:Par_Eden_Space:used': 'jvm.mem.current.Par_Eden_Space.used',
            'jvm:mem:current:Par_Survivor_Space:max': 'jvm.mem.current.Par_Survivor_Space.max',
            'jvm:mem:current:Par_Survivor_Space:used': 'jvm.mem.current.Par_Survivor_Space.used',
            'jvm:mem:current:Compressed_Class_Space:max': 'jvm.mem.current.Compressed_Class_Space.max',
            'jvm:mem:current:Compressed_Class_Space:used': 'jvm.mem.current.Compressed_Class_Space.used',
            'jvm:mem:current:Code_Cache:max': 'jvm.mem.current.Code_Cache.max',
            'jvm:mem:current:Code_Cache:used': 'jvm.mem.current.Code_Cache.used',
            'jvm:num_cpus': 'jvm.num_cpus',
            'jvm:gc:msec': 'jvm.gc.msec',
            'jvm:gc:ParNew:msec': 'jvm.gc.ParNew.msec',
            'jvm:gc:ParNew:cycles': 'jvm.gc.ParNew.cycles',
            'jvm:gc:ConcurrentMarkSweep:msec': 'jvm.gc.ConcurrentMarkSweep.msec',
            'jvm:gc:ConcurrentMarkSweep:cycles': 'jvm.gc.ConcurrentMarkSweep.cycles',
            'jvm:gc:cycles': 'jvm.gc.cycles',
            'jvm:fd_limit': 'jvm.fd_limit',
            'jvm:compilation:time_msec': 'jvm.compilation.time_msec',
            'jvm:uptime': 'jvm.uptime',
            'jvm:safepoint:sync_time_millis': 'jvm.safepoint.sync_time_millis',
            'jvm:safepoint:total_time_millis': 'jvm.safepoint.total_time_millis',
            'jvm:safepoint:count': 'jvm.safepoint.count',
            'jvm:heap:committed': 'jvm.heap.committed',
            'jvm:heap:max': 'jvm.heap.max',
            'jvm:heap:used': 'jvm.heap.used',
            'jvm:fd_count': 'jvm.fd_count',
            'rt:server:sent_bytes': 'rt.server.sent_bytes',
            'rt:server:connects': 'rt.server.connects',
            'rt:server:success': 'rt.server.success',
            'rt:server:received_bytes': 'rt.server.received_bytes',
            'rt:server:read_timeout': 'rt.server.read_timeout',
            'rt:server:write_timeout': 'rt.server.write_timeout',
            'rt:server:nacks': 'rt.server.nacks',
            'rt:server:thread_usage:requests:mean': 'rt.server.thread_usage.requests.mean',
            'rt:server:thread_usage:requests:relative_stddev': 'rt.server.thread_usage.requests.relative_stddev',
            'rt:server:thread_usage:requests:stddev': 'rt.server.thread_usage.requests.stddev',
            'rt:server:socket_unwritable_ms': 'rt.server.socket_unwritable_ms',
            'rt:server:closes': 'rt.server.closes',
            'rt:server:status:1XX': 'rt.server.status.1XX',
            'rt:server:status:4XX': 'rt.server.status.4XX',
            'rt:server:status:2XX': 'rt.server.status.2XX',
            'rt:server:status:error': 'rt.server.status.error',
            'rt:server:status:3XX': 'rt.server.status.3XX',
            'rt:server:status:5XX': 'rt.server.status.5XX',
            'rt:server:nonretryable_nacks': 'rt.server.nonretryable_nacks',
            'rt:server:socket_writable_ms': 'rt.server.socket_writable_ms',
            'rt:server:requests': 'rt.server.requests',
            'rt:server:pending': 'rt.server.pending',
            'rt:server:connections': 'rt.server.connections',
            'rt:bindcache:path:expires': 'rt.bindcache.path.expires',
            'rt:bindcache:path:evicts': 'rt.bindcache.path.evicts',
            'rt:bindcache:path:misses': 'rt.bindcache.path.misses',
            'rt:bindcache:path:oneshots': 'rt.bindcache.path.oneshots',
            'rt:bindcache:bound:expires': 'rt.bindcache.bound.expires',
            'rt:bindcache:bound:evicts': 'rt.bindcache.bound.evicts',
            'rt:bindcache:bound:misses': 'rt.bindcache.bound.misses',
            'rt:bindcache:bound:oneshots': 'rt.bindcache.bound.oneshots',
            'rt:bindcache:tree:expires': 'rt.bindcache.tree.expires',
            'rt:bindcache:tree:evicts': 'rt.bindcache.tree.evicts',
            'rt:bindcache:tree:misses': 'rt.bindcache.tree.misses',
            'rt:bindcache:tree:oneshots': 'rt.bindcache.tree.oneshots',
            'rt:bindcache:client:expires': 'rt.bindcache.client.expires',
            'rt:bindcache:client:evicts': 'rt.bindcache.client.evicts',
            'rt:bindcache:client:misses': 'rt.bindcache.client.misses',
            'rt:bindcache:client:oneshots': 'rt.bindcache.client.oneshots',
        }

        types_map = {
            'jvm:start_time': 'gauge',
            'jvm:application_time_millis': 'gauge',
            'jvm:classes:total_loaded': 'gauge',
            'jvm:classes:current_loaded': 'gauge',
            'jvm:classes:total_unloaded': 'gauge',
            'jvm:postGC:Par_Survivor_Space:max': 'gauge',
            'jvm:postGC:Par_Survivor_Space:used': 'gauge',
            'jvm:postGC:CMS_Old_Gen:max': 'gauge',
            'jvm:postGC:CMS_Old_Gen:used': 'gauge',
            'jvm:postGC:Par_Eden_Space:max': 'gauge',
            'jvm:postGC:Par_Eden_Space:used': 'gauge',
            'jvm:postGC:used': 'gauge',
            'jvm:nonheap:committed': 'gauge',
            'jvm:nonheap:max': 'gauge',
            'jvm:nonheap:used': 'gauge',
            'jvm:tenuring_threshold': 'gauge',
            'jvm:thread:daemon_count': 'gauge',
            'jvm:thread:count': 'gauge',
            'jvm:thread:peak_count': 'gauge',
            'jvm:mem:postGC:Par_Survivor_Space:max': 'gauge',
            'jvm:mem:postGC:Par_Survivor_Space:used': 'gauge',
            'jvm:mem:postGC:CMS_Old_Gen:max': 'gauge',
            'jvm:mem:postGC:CMS_Old_Gen:used': 'gauge',
            'jvm:mem:postGC:Par_Eden_Space:max': 'gauge',
            'jvm:mem:postGC:Par_Eden_Space:used': 'gauge',
            'jvm:mem:postGC:used': 'gauge',
            'jvm:mem:metaspace:max_capacity': 'gauge',
            'jvm:mem:buffer:direct:max': 'gauge',
            'jvm:mem:buffer:direct:count': 'gauge',
            'jvm:mem:buffer:direct:used': 'gauge',
            'jvm:mem:buffer:mapped:max': 'gauge',
            'jvm:mem:buffer:mapped:count': 'gauge',
            'jvm:mem:buffer:mapped:used': 'gauge',
            'jvm:mem:allocations:eden:bytes': 'gauge',
            'jvm:mem:current:used': 'gauge',
            'jvm:mem:current:CMS_Old_Gen:max': 'gauge',
            'jvm:mem:current:CMS_Old_Gen:used': 'gauge',
            'jvm:mem:current:Metaspace:max': 'gauge',
            'jvm:mem:current:Metaspace:used': 'gauge',
            'jvm:mem:current:Par_Eden_Space:max': 'gauge',
            'jvm:mem:current:Par_Eden_Space:used': 'gauge',
            'jvm:mem:current:Par_Survivor_Space:max': 'gauge',
            'jvm:mem:current:Par_Survivor_Space:used': 'gauge',
            'jvm:mem:current:Compressed_Class_Space:max': 'gauge',
            'jvm:mem:current:Compressed_Class_Space:used': 'gauge',
            'jvm:mem:current:Code_Cache:max': 'gauge',
            'jvm:mem:current:Code_Cache:used': 'gauge',
            'jvm:num_cpus': 'gauge',
            'jvm:gc:msec': 'gauge',
            'jvm:gc:ParNew:msec': 'gauge',
            'jvm:gc:ParNew:cycles': 'gauge',
            'jvm:gc:ConcurrentMarkSweep:msec': 'gauge',
            'jvm:gc:ConcurrentMarkSweep:cycles': 'gauge',
            'jvm:gc:cycles': 'gauge',
            'jvm:fd_limit': 'gauge',
            'jvm:compilation:time_msec': 'gauge',
            'jvm:uptime': 'gauge',
            'jvm:safepoint:sync_time_millis': 'gauge',
            'jvm:safepoint:total_time_millis': 'gauge',
            'jvm:safepoint:count': 'gauge',
            'jvm:heap:committed': 'gauge',
            'jvm:heap:max': 'gauge',
            'jvm:heap:used': 'gauge',
            'jvm:fd_count': 'gauge',
            'rt:server:sent_bytes': 'gauge',
            'rt:server:connects': 'gauge',
            'rt:server:success': 'gauge',
            'rt:server:received_bytes': 'gauge',
            'rt:server:read_timeout': 'gauge',
            'rt:server:write_timeout': 'gauge',
            'rt:server:nacks': 'gauge',
            'rt:server:thread_usage:requests:mean': 'gauge',
            'rt:server:thread_usage:requests:relative_stddev': 'gauge',
            'rt:server:thread_usage:requests:stddev': 'gauge',
            'rt:server:socket_unwritable_ms': 'gauge',
            'rt:server:closes': 'gauge',
            'rt:server:status:1XX': 'gauge',
            'rt:server:status:4XX': 'gauge',
            'rt:server:status:2XX': 'gauge',
            'rt:server:status:error': 'gauge',
            'rt:server:status:3XX': 'gauge',
            'rt:server:status:5XX': 'gauge',
            'rt:server:nonretryable_nacks': 'gauge',
            'rt:server:socket_writable_ms': 'gauge',
            'rt:server:requests': 'gauge',
            'rt:server:pending': 'gauge',
            'rt:server:connections': 'gauge',
            'rt:bindcache:path:expires': 'gauge',
            'rt:bindcache:path:evicts': 'gauge',
            'rt:bindcache:path:misses': 'gauge',
            'rt:bindcache:path:oneshots': 'gauge',
            'rt:bindcache:bound:expires': 'gauge',
            'rt:bindcache:bound:evicts': 'gauge',
            'rt:bindcache:bound:misses': 'gauge',
            'rt:bindcache:bound:oneshots': 'gauge',
            'rt:bindcache:tree:expires': 'gauge',
            'rt:bindcache:tree:evicts': 'gauge',
            'rt:bindcache:tree:misses': 'gauge',
            'rt:bindcache:tree:oneshots': 'gauge',
            'rt:bindcache:client:expires': 'gauge',
            'rt:bindcache:client:evicts': 'gauge',
            'rt:bindcache:client:misses': 'gauge',
            'rt:bindcache:client:oneshots': 'gauge',
        }

        self.log.error(self.init_config)
        self.log.error(self.agentConfig)

        # Linkerd allows you to add a prefix for the metrics in the configuration
        prefix = self.init_config.get("linkerd_prometheus_prefix", '')
        for m in metrics_map:
            self.metrics_mapper[prefix + m] = metrics_map[m]
        for m in types_map:
            self.type_overrides[prefix + m] = types_map[m]


    def check(self, instance):
        endpoint = instance.get('prometheus_endpoint')
        if endpoint is None:
            raise Exception("Unable to find prometheus_endpoint in config file.")

        send_buckets = instance.get('send_histograms_buckets', True)
        # By default we send the buckets.
        if send_buckets is not None and str(send_buckets).lower() == 'false':
            send_buckets = False
        else:
            send_buckets = True

        self.process(endpoint, send_histograms_buckets=send_buckets, instance=instance)
