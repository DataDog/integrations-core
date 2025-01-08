# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheck

DEFAULT_METRICS = {
    'admission_webhooks_certificate_expiry': 'admission_webhooks.certificate_expiry',
    'admission_webhooks_cws_exec_instrumentation_attempts': 'admission_webhooks.cws_exec_instrumentation_attempts',
    'admission_webhooks_cws_pod_instrumentation_attempts': 'admission_webhooks.cws_pod_instrumentation_attempts',
    'admission_webhooks_library_injection_attempts': 'admission_webhooks.library_injection_attempts',
    'admission_webhooks_library_injection_errors': 'admission_webhooks.library_injection_errors',
    'admission_webhooks_mutation_attempts': 'admission_webhooks.mutation_attempts',
    'admission_webhooks_validation_attempts': 'admission_webhooks.validation_attempts',
    'admission_webhooks_patcher_attempts': 'admission_webhooks.patcher.attempts',
    'admission_webhooks_patcher_completed': 'admission_webhooks.patcher.completed',
    'admission_webhooks_patcher_errors': 'admission_webhooks.patcher.errors',
    'admission_webhooks_rc_provider_configs': 'admission_webhooks.rc_provider.configs',
    'admission_webhooks_rc_provider_configs_invalid': 'admission_webhooks.rc_provider.invalid_configs',
    'admission_webhooks_reconcile_errors': 'admission_webhooks.reconcile_errors',
    'admission_webhooks_reconcile_success': 'admission_webhooks.reconcile_success',
    'admission_webhooks_response_duration': 'admission_webhooks.response_duration',
    'admission_webhooks_webhooks_received': 'admission_webhooks.webhooks_received',
    'autoscaling_workload_autoscaler_conditions': 'autoscaling.workload.autoscaler_conditions',
    'autoscaling_workload_horizontal_scaling_actions': 'autoscaling.workload.horizontal_scaling_actions',
    'autoscaling_workload_horizontal_scaling_applied_replicas': 'autoscaling.workload.horizontal_scaling_applied_replicas',  # noqa: E501
    'autoscaling_workload_horizontal_scaling_received_replicas': 'autoscaling.workload.horizontal_scaling_received_replicas',  # noqa: E501
    'autoscaling_workload_queue_adds': 'autoscaling.workload.queue_adds',
    'autoscaling_workload_queue_depth': 'autoscaling.workload.queue_depth',
    'autoscaling_workload_queue_latency': 'autoscaling.workload.queue_latency',
    'autoscaling_workload_queue_longest_running_processor': 'autoscaling.workload.queue_longest_running_processor',
    'autoscaling_workload_queue_retries': 'autoscaling.workload.queue_retries',
    'autoscaling_workload_queue_unfinished_work': 'autoscaling.workload.queue_unfinished_work',
    'autoscaling_workload_queue_work_duration': 'autoscaling.workload.queue_work_duration',
    'autoscaling_workload_vertical_rollout_triggered': 'autoscaling.workload.vertical_rollout_triggered',
    'autoscaling_workload_vertical_scaling_received_limits': 'autoscaling.workload.vertical_scaling_received_limits',
    'autoscaling_workload_vertical_scaling_received_requests': 'autoscaling.workload.vertical_scaling_received_requests',  # noqa: E501
    'autoscaling_workload_store_load_entities': 'autoscaling.workload.store_load_entities',
    'autoscaling_workload_store_job_queue_length': 'autoscaling.workload.store_job_queue_length',
    'aggregator__flush': 'aggregator.flush',
    'aggregator__processed': 'aggregator.processed',
    'api_requests': 'api_requests',
    'autodiscovery_errors': 'autodiscovery.errors',
    'autodiscovery_poll_duration': 'autodiscovery.poll_duration',
    'autodiscovery_watched_resources': 'autodiscovery.watched_resources',
    'cluster_checks_busyness': 'cluster_checks.busyness',
    'cluster_checks_configs_dangling': 'cluster_checks.configs_dangling',
    'cluster_checks_configs_dispatched': 'cluster_checks.configs_dispatched',
    'cluster_checks_unscheduled_check': 'cluster_checks.unscheduled_check',
    'cluster_checks_configs_info': 'cluster_checks.configs_info',
    'cluster_checks_failed_stats_collection': 'cluster_checks.failed_stats_collection',
    'cluster_checks_nodes_reporting': 'cluster_checks.nodes_reporting',
    'cluster_checks_rebalancing_decisions': 'cluster_checks.rebalancing_decisions',
    'cluster_checks_rebalancing_duration_seconds': 'cluster_checks.rebalancing_duration_seconds',
    'cluster_checks_successful_rebalancing_moves': 'cluster_checks.successful_rebalancing_moves',
    'cluster_checks_updating_stats_duration_seconds': 'cluster_checks.updating_stats_duration_seconds',
    'datadog_requests': 'datadog.requests',
    'endpoint_checks_configs_dispatched': 'endpoint_checks.configs_dispatched',
    'external_metrics': 'external_metrics',
    'external_metrics_api_elapsed': 'external_metrics.api_elapsed',
    'external_metrics_api_requests': 'external_metrics.api_requests',
    'external_metrics_datadog_metrics': 'external_metrics.datadog_metrics',
    'external_metrics_delay_seconds': 'external_metrics.delay_seconds',
    'external_metrics_processed_value': 'external_metrics.processed_value',
    'go_goroutines': 'go.goroutines',
    'go_memstats_alloc_bytes': 'go.memstats.alloc_bytes',
    'go_threads': 'go.threads',
    'kubernetes_apiserver_emitted_events': 'kubernetes_apiserver.emitted_events',
    'kubernetes_apiserver_kube_events': 'kubernetes_apiserver.kube_events',
    'language_detection_dca_handler_processed_requests': 'language_detection_dca_handler.processed_requests',
    'language_detection_patcher_patches': 'language_detection_patcher.patches',
    'rate_limit_queries_limit': 'datadog.rate_limit_queries.limit',
    'rate_limit_queries_period': 'datadog.rate_limit_queries.period',
    'rate_limit_queries_remaining': 'datadog.rate_limit_queries.remaining',
    'rate_limit_queries_remaining_min': 'datadog.rate_limit_queries.remaining_min',
    'rate_limit_queries_reset': 'datadog.rate_limit_queries.reset',
    'secret_backend__elapsed_ms': 'secret_backend.elapsed',
    'tagger_stored_entities': 'tagger.stored_entities',
    'tagger_updated_entities': 'tagger.updated_entities',
    'workloadmeta_events_received': 'workloadmeta.events_received',
    'workloadmeta_notifications_sent': 'workloadmeta.notifications_sent',
    'workloadmeta_stored_entities': 'workloadmeta.stored_entities',
    'workloadmeta_subscribers': 'workloadmeta.subscribers',
}


class DatadogClusterAgentCheck(OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(DatadogClusterAgentCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                'datadog.cluster_agent': {
                    'prometheus_url': 'http://localhost:5000/metrics',
                    'namespace': 'datadog.cluster_agent',
                    'metrics': [DEFAULT_METRICS],
                    'label_joins': {
                        'leader_election_is_leader': {
                            'labels_to_match': ['*'],
                            'labels_to_get': ['is_leader'],
                        }
                    },
                    'send_histograms_buckets': True,
                    'send_distribution_counts_as_monotonic': True,
                    'send_distribution_sums_as_monotonic': True,
                }
            },
            default_namespace='datadog.cluster_agent',
        )
