# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from copy import deepcopy

from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.errors import CheckException


class Istio(OpenMetricsBaseCheck):
    MIXER_NAMESPACE = 'istio.mixer'
    MESH_NAMESPACE = 'istio.mesh'
    PILOT_NAMESPACE = 'istio.pilot'
    GALLEY_NAMESPACE = 'istio.galley'
    CITADEL_NAMESPACE = 'istio.citadel'
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
        Process all the endpoints associated with this instance.
        All the endpoints themselves are optional, but at least one must be passed.
        """
        processed = False
        # Get the config for the istio_mesh instance
        istio_mesh_endpoint = instance.get('istio_mesh_endpoint')
        if istio_mesh_endpoint:
            istio_mesh_config = self.config_map[istio_mesh_endpoint]

            # Process istio_mesh
            self.process(istio_mesh_config)
            processed = True

        # Get the config for the process_mixer instance
        process_mixer_endpoint = instance.get('mixer_endpoint')
        if process_mixer_endpoint:
            process_mixer_config = self.config_map[process_mixer_endpoint]

            # Process process_mixer
            self.process(process_mixer_config)
            processed = True

        # Get the config for the process_pilot instance
        process_pilot_endpoint = instance.get('pilot_endpoint')
        if process_pilot_endpoint:
            process_pilot_config = self.config_map[process_pilot_endpoint]

            # Process process_pilot
            self.process(process_pilot_config)
            processed = True

        # Get the config for the process_galley instance
        process_galley_endpoint = instance.get('galley_endpoint')
        if process_galley_endpoint:
            process_galley_config = self.config_map[process_galley_endpoint]

            # Process process_galley
            self.process(process_galley_config)
            processed = True

        # Get the config for the process_citadel instance
        process_citadel_endpoint = instance.get('citadel_endpoint')
        if process_citadel_endpoint:
            process_citadel_config = self.config_map[process_citadel_endpoint]

            # Process process_citadel
            self.process(process_citadel_config)
            processed = True

        # Check that at least 1 endpoint is configured
        if not processed:
            raise CheckException("At least one of Mixer, Mesh, Pilot, Galley or Citadel endpoints must be configured")

    def create_generic_instances(self, instances):
        """
        Generalize each (single) Istio instance into OpenMetricsBaseCheck instances.
        """
        result = []
        for instance in instances:
            if 'istio_mesh_endpoint' in instance:
                result.append(self._create_istio_mesh_instance(instance))
            if 'mixer_endpoint' in instance:
                result.append(self._create_process_mixer_instance(instance))
            if 'pilot_endpoint' in instance:
                result.append(self._create_process_pilot_instance(instance))
            if 'galley_endpoint' in instance:
                result.append(self._create_process_galley_instance(instance))
            if 'citadel_endpoint' in instance:
                result.append(self._create_process_citadel_instance(instance))
        return result

    @staticmethod
    def _get_generic_metrics():
        return {
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
            'process_cpu_seconds_total': 'process.cpu_seconds_total',
            'process_max_fds': 'process.max_fds',
            'process_open_fds': 'process.open_fds',
            'process_resident_memory_bytes': 'process.resident_memory_bytes',
            'process_start_time_seconds': 'process.start_time_seconds',
            'process_virtual_memory_bytes': 'process.virtual_memory_bytes',
        }

    def _create_istio_mesh_instance(self, instance):
        """
        Grab the istio mesh scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('istio_mesh_endpoint')

        istio_mesh_instance = deepcopy(instance)
        istio_mesh_instance.update(
            {
                'namespace': self.MESH_NAMESPACE,
                'prometheus_url': endpoint,
                'label_to_hostname': endpoint,
                'metrics': [
                    {
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
                ],
                # Defaults that were set when istio was based on PrometheusCheck
                'send_monotonic_counter': instance.get('send_monotonic_counter', False),
                'health_service_check': instance.get('health_service_check', False),
            }
        )

        return istio_mesh_instance

    def _create_process_mixer_instance(self, instance):
        """
        Grab the mixer scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('mixer_endpoint')

        process_mixer_instance = deepcopy(instance)
        process_mixer_instance.update(
            {
                'namespace': self.MIXER_NAMESPACE,
                'prometheus_url': endpoint,
                'metrics': [
                    {
                        # Pre 1.1 metrics
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
                        # 1.1 metrics
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
                        'mixer_runtime_dispatches_total': 'runtime.dispatches_total',
                        'mixer_runtime_dispatch_duration_seconds': 'runtime.dispatch_duration_seconds',
                    }
                ],
                # Defaults that were set when istio was based on PrometheusCheck
                'send_monotonic_counter': instance.get('send_monotonic_counter', False),
                'health_service_check': instance.get('health_service_check', False),
            }
        )
        process_mixer_instance['metrics'][0].update(self._get_generic_metrics())

        return process_mixer_instance

    def _create_process_pilot_instance(self, instance):
        """
        Grab the pilot scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('pilot_endpoint')

        process_pilot_instance = deepcopy(instance)
        process_pilot_instance.update(
            {
                'namespace': self.PILOT_NAMESPACE,
                'prometheus_url': endpoint,
                'metrics': [
                    {
                        'pilot_conflict_inbound_listener': 'conflict.inbound_listener',
                        'pilot_conflict_outbound_listener_http_over_current_tcp': (
                            'conflict.outbound_listener.http_over_current_tcp'
                        ),
                        'pilot_conflict_outbound_listener_tcp_over_current_http': (
                            'conflict.outbound_listener.tcp_over_current_http'
                        ),
                        'pilot_conflict_outbound_listener_tcp_over_current_tcp': (
                            'conflict.outbound_listener.tcp_over_current_tcp'
                        ),
                        'pilot_destrule_subsets': 'destrule_subsets',
                        'pilot_duplicate_envoy_clusters': 'duplicate_envoy_clusters',
                        'pilot_eds_no_instances': 'eds_no_instances',
                        'pilot_endpoint_not_ready': 'endpoint_not_ready',
                        'pilot_invalid_out_listeners': 'invalid_out_listeners',
                        'pilot_mcp_sink_reconnections': 'mcp_sink.reconnections',
                        'pilot_mcp_sink_recv_failures_total': 'mcp_sink.recv_failures_total',
                        'pilot_mcp_sink_request_acks_total': 'mcp_sink.request_acks_total',
                        'pilot_no_ip': 'no_ip',
                        'pilot_proxy_convergence_time': 'proxy_convergence_time',
                        'pilot_rds_expired_nonce': 'rds_expired_nonce',
                        'pilot_services': 'services',
                        'pilot_total_xds_internal_errors': 'total_xds_internal_errors',
                        'pilot_total_xds_rejects': 'total_xds_rejects',
                        'pilot_virt_services': 'virt_services',
                        'pilot_vservice_dup_domain': 'vservice_dup_domain',
                        'pilot_xds': 'xds',
                        'pilot_xds_eds_instances': 'xds.eds_instances',
                        'pilot_xds_push_context_errors': 'xds.push.context_errors',
                        'pilot_xds_push_timeout': 'xds.push.timeout',
                        'pilot_xds_push_timeout_failures': 'xds.push.timeout_failures',
                        'pilot_xds_pushes': 'xds.pushes',
                        'pilot_xds_write_timeout': 'xds.write_timeout',
                    }
                ],
            }
        )
        process_pilot_instance['metrics'][0].update(self._get_generic_metrics())
        return process_pilot_instance

    def _create_process_galley_instance(self, instance):
        """
        Grab the galley scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('galley_endpoint')

        process_galley_instance = deepcopy(instance)
        process_galley_instance.update(
            {
                'namespace': self.GALLEY_NAMESPACE,
                'prometheus_url': endpoint,
                'metrics': [
                    {
                        'endpoint_no_pod': 'endpoint_no_pod',
                        'galley_mcp_source_clients_total': 'mcp_source.clients_total',
                        'galley_runtime_processor_event_span_duration_milliseconds': (
                            'runtime_processor.event_span_duration_milliseconds'
                        ),
                        'galley_runtime_processor_events_processed_total': 'runtime_processor.events_processed_total',
                        'galley_runtime_processor_snapshot_events_total': 'runtime_processor.snapshot_events_total',
                        'galley_runtime_processor_snapshot_lifetime_duration_milliseconds': (
                            'runtime_processor.snapshot_lifetime_duration_milliseconds'
                        ),
                        'galley_runtime_processor_snapshots_published_total': (
                            'runtime_processor.snapshots_published_total'
                        ),
                        'galley_runtime_state_type_instances_total': 'runtime_state_type_instances_total',
                        'galley_runtime_strategy_on_change_total': 'runtime_strategy.on_change_total',
                        'galley_runtime_strategy_timer_max_time_reached_total': (
                            'runtime_strategy.timer_max_time_reached_total'
                        ),
                        'galley_runtime_strategy_timer_quiesce_reached_total': 'runtime_strategy.quiesce_reached_total',
                        'galley_runtime_strategy_timer_resets_total': 'runtime_strategy.timer_resets_total',
                        'galley_source_kube_dynamic_converter_success_total': (
                            'source_kube.dynamic_converter_success_total'
                        ),
                        'galley_source_kube_event_success_total': 'source_kube.event_success_total',
                        'galley_validation_cert_key_updates': 'validation.cert_key_updates',
                        'galley_validation_config_load': 'validation.config_load',
                        'galley_validation_config_updates': 'validation.config_update',
                        'galley_validation_passed': 'validation.passed',
                    }
                ],
                # The following metrics have been blakclisted due to high cardinality of tags
                'ignore_metrics': ['galley_mcp_source_message_size_bytes', 'galley_mcp_source_request_acks_total'],
            }
        )
        process_galley_instance['ignore_metrics'].extend(instance.get('ignore_metrics', []))
        process_galley_instance['metrics'][0].update(self._get_generic_metrics())
        return process_galley_instance

    def _create_process_citadel_instance(self, instance):
        """
        Grab the citadel scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('citadel_endpoint')

        process_citadel_instance = deepcopy(instance)
        process_citadel_instance.update(
            {
                'namespace': self.CITADEL_NAMESPACE,
                'prometheus_url': endpoint,
                'metrics': [
                    {
                        'citadel_secret_controller_csr_err_count': 'secret_controller.csr_err_count',
                        'citadel_secret_controller_secret_deleted_cert_count': (
                            'secret_controller.secret_deleted_cert_count'
                        ),
                        'citadel_secret_controller_svc_acc_created_cert_count': (
                            'secret_controller.svc_acc_created_cert_count'
                        ),
                        'citadel_secret_controller_svc_acc_deleted_cert_count': (
                            'secret_controller.svc_acc_deleted_cert_count'
                        ),
                        'citadel_server_authentication_failure_count': 'server.authentication_failure_count',
                        'citadel_server_citadel_root_cert_expiry_timestamp': (
                            'server.citadel_root_cert_expiry_timestamp'
                        ),
                        'citadel_server_csr_count': 'server.csr_count',
                        'citadel_server_csr_parsing_err_count': 'server.csr_parsing_err_count',
                        'citadel_server_id_extraction_err_count': 'server.id_extraction_err_count',
                        'citadel_server_success_cert_issuance_count': 'server.success_cert_issuance_count',
                    }
                ],
            }
        )
        process_citadel_instance['metrics'][0].update(self._get_generic_metrics())
        return process_citadel_instance
