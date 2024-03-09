# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRICS_MAP = {
    'admission_webhooks_certificate_expiry': 'admission_webhooks.certificate_expiry',
    'admission_webhooks_library_injection_attempts': 'admission_webhooks.library_injection_attempts',
    'admission_webhooks_library_injection_errors': 'admission_webhooks.library_injection_errors',
    'admission_webhooks_mutation_attempts': 'admission_webhooks.mutation_attempts',
    'admission_webhooks_mutation_errors': 'admission_webhooks.mutation_errors',
    'admission_webhooks_patcher_attempts': 'admission_webhooks.patcher.attempts',
    'admission_webhooks_patcher_completed': 'admission_webhooks.patcher.completed',
    'admission_webhooks_patcher_errors': 'admission_webhooks.patcher.errors',
    'admission_webhooks_rc_provider_configs': 'admission_webhooks.rc_provider.configs',
    'admission_webhooks_rc_provider_configs_invalid': 'admission_webhooks.rc_provider.invalid_configs',
    'admission_webhooks_reconcile_errors': 'admission_webhooks.reconcile_errors',
    'admission_webhooks_reconcile_success': 'admission_webhooks.reconcile_success',
    'admission_webhooks_response_duration': 'admission_webhooks.response_duration',
    'admission_webhooks_webhooks_received': 'admission_webhooks.webhooks_received',
    'aggregator__flush': 'aggregator.flush',
    'aggregator__processed': 'aggregator.processed',
    'api_requests': 'api_requests',
    'autodiscovery_errors': 'autodiscovery.errors',
    'autodiscovery_poll_duration': 'autodiscovery.poll_duration',
    'autodiscovery_watched_resources': 'autodiscovery.watched_resources',
    'cluster_checks_busyness': 'cluster_checks.busyness',
    'cluster_checks_configs_dangling': 'cluster_checks.configs_dangling',
    'cluster_checks_configs_dispatched': 'cluster_checks.configs_dispatched',
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
}


def construct_metrics_config(metric_map, type_overrides):
    metrics = []
    for raw_metric_name, metric_name in metric_map.items():
        if raw_metric_name.endswith('_total'):
            raw_metric_name = raw_metric_name[:-6]
            metric_name = metric_name[:-6]
        elif metric_name.endswith('.count'):
            metric_name = metric_name[:-6]

        config = {raw_metric_name: {'name': metric_name}}
        if raw_metric_name in type_overrides:
            config[raw_metric_name]['type'] = type_overrides[raw_metric_name]

        metrics.append(config)

    return metrics
