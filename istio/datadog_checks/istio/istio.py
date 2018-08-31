# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from copy import deepcopy

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.errors import CheckException


class Istio(OpenMetricsBaseCheck):
    MIXER_NAMESPACE = 'istio.mixer'
    MESH_NAMESPACE = 'istio.mesh'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, agentConfig, instances=None):

        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        # Set up OpenMetricsBaseCheck with our generic instances
        super(Istio, self).__init__(name, init_config, agentConfig, instances=generic_instances)

    def check(self, instance):
        """
        Process both the istio_mesh instance and process_mixer instance associated with this instance
        """

        # Get the config for the istio_mesh instance
        istio_mesh_endpoint = instance.get('istio_mesh_endpoint')
        istio_mesh_config = self.config_map[istio_mesh_endpoint]

        # Process istio_mesh
        self.process(istio_mesh_config)

        # Get the config for the process_mixer instance
        process_mixer_endpoint = instance.get('mixer_endpoint')
        process_mixer_config = self.config_map[process_mixer_endpoint]

        # Process process_mixer
        self.process(process_mixer_config)

    def create_generic_instances(self, instances):
        """
        Generalize each (single) Istio instance into two OpenMetricsBaseCheck instances
        """
        generic_instances = []

        for instance in instances:
            istio_mesh_instance = self._create_istio_mesh_instance(instance)
            process_mixer_instance = self._create_process_mixer_instance(instance)

            generic_instances.extend([istio_mesh_instance, process_mixer_instance])

        return generic_instances

    def _create_istio_mesh_instance(self, instance):
        """
        Grab the istio mesh scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict
        """
        endpoint = instance.get('istio_mesh_endpoint')

        if endpoint is None:
            raise CheckException("Unable to find istio_mesh_endpoint in config file.")

        istio_mesh_instance = deepcopy(instance)
        istio_mesh_instance.update({
            'namespace': self.MESH_NAMESPACE,
            'prometheus_url': endpoint,
            'label_to_hostname': endpoint,
            'metrics': [{
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
            }],
            # Defaults that were set when istio was based on PrometheusCheck
            'send_monotonic_counter': instance.get('send_monotonic_counter', False),
            'health_service_check': instance.get('health_service_check', False)
        })

        return istio_mesh_instance

    def _create_process_mixer_instance(self, instance):
        """
        Grab the mixer scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict
        """
        endpoint = instance.get('mixer_endpoint')
        if endpoint is None:
            raise CheckException("Unable to find mixer_endpoint in config file.")

        process_mixer_instance = deepcopy(instance)
        process_mixer_instance.update({
            'namespace': self.MIXER_NAMESPACE,
            'prometheus_url': endpoint,
            'metrics': [{
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
            }],
            # Defaults that were set when istio was based on PrometheusCheck
            'send_monotonic_counter': instance.get('send_monotonic_counter', False),
            'health_service_check': instance.get('health_service_check', False)
        })

        return process_mixer_instance
