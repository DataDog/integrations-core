# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.checks.prometheus import PrometheusScraper, PrometheusCheck


class Istio(PrometheusCheck):
    MIXER_NAMESPACE = 'istio.mixer'
    MESH_NAMESPACE = 'istio.mesh'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(Istio, self).__init__(name, init_config, agentConfig, instances)
        self._scrapers = {}

    def check(self, instance):
        self._process_istio_mesh(instance)
        self._process_mixer(instance)

    def _process_istio_mesh(self, instance):
        """
        Grab the scraper and run the process function for istio mesh
        """
        self.log.debug('setting up mesh scraper')
        endpoint = instance.get('istio_mesh_endpoint')
        scraper = self._get_istio_mesh_scraper(instance)
        self.log.debug('processing mesh metrics')
        scraper.process(
            endpoint,
            send_histograms_buckets=instance.get('send_histograms_buckets', True),
            instance=instance,
            ignore_unmapped=True
        )

    def _process_mixer(self, instance):
        """
        Grab the scraper and run the process function for the mixer
        """
        self.log.debug('setting up mixer scraper')
        endpoint = instance.get('mixer_endpoint')
        scraper = self._get_mixer_scraper(instance)
        self.log.debug('processing mixer metrics')
        scraper.process(
            endpoint,
            send_histograms_buckets=instance.get('send_histograms_buckets', True),
            instance=instance,
            ignore_unmapped=True
        )

    def _get_istio_mesh_scraper(self, instance):
        """
        Grab the istio mesh scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict
        """
        endpoint = instance.get('istio_mesh_endpoint')

        if self._scrapers.get(endpoint, None):
            return self._scrapers.get(endpoint)

        scraper = PrometheusScraper(self)
        self._scrapers[endpoint] = scraper
        scraper.NAMESPACE = self.MESH_NAMESPACE
        scraper.metrics_mapper = {
            # These metrics support Istio 1.0
            'istio_requests_total': 'request.count',
            'istio_request_duration_seconds': 'request.duration',
            'istio_request_bytes': 'request.size',
            'istio_response_bytes': 'response.size',

            # These metrics support Istio 0.8
            'istio_request_count': 'request.count',
            'istio_request_duration': 'request.duration',
            'istio_request_size': 'request.size',
            'istio_response_size': 'response.size',
        }
        scraper.label_to_hostname = endpoint
        scraper = self._shared_scraper_config(scraper, instance)

        return scraper

    def _get_mixer_scraper(self, instance):
        """
        Grab the mixer scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict
        """
        endpoint = instance.get('mixer_endpoint')

        if self._scrapers.get(endpoint, None):
            return self._scrapers.get(endpoint)

        scraper = PrometheusScraper(self)
        self._scrapers[endpoint] = scraper
        scraper.NAMESPACE = self.MIXER_NAMESPACE
        scraper.metrics_mapper = {
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
        scraper = self._shared_scraper_config(scraper, instance)
        return scraper

    def _shared_scraper_config(self, scraper, instance):
        """
        Configuration that is shared by both scrapers
        """
        scraper.labels_mapper = instance.get("labels_mapper", {})
        scraper.label_joins = instance.get("label_joins", {})
        scraper.type_overrides = instance.get("type_overrides", {})
        scraper.exclude_labels = instance.get("exclude_labels", [])
        # For simple values instance settings overrides optional defaults
        scraper.health_service_check = instance.get("health_service_check", True)
        scraper.ssl_cert = instance.get("ssl_cert", None)
        scraper.ssl_private_key = instance.get("ssl_private_key", None)
        scraper.ssl_ca_cert = instance.get("ssl_ca_cert", None)

        return scraper
