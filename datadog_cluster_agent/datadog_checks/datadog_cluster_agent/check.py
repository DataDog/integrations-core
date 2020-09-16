# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck

DEFAULT_METRICS = {
    'admission_webhooks_certificate_expiry': 'admission_webhooks.certificate_expiry',
    'admission_webhooks_mutation_attempts': 'admission_webhooks.mutation_attempts',
    'admission_webhooks_reconcile_success': 'admission_webhooks.reconcile_success',
    'admission_webhooks_webhooks_received': 'admission_webhooks.webhooks_received',
    'cluster_checks_busyness': 'cluster_checks.busyness',
    'cluster_checks_configs_dangling': 'cluster_checks.configs_dangling',
    'cluster_checks_configs_dispatched': 'cluster_checks.configs_dispatched',
    'cluster_checks_nodes_reporting': 'cluster_checks.nodes_reporting',
    'cluster_checks_rebalancing_decisions': 'cluster_checks.rebalancing_decisions',
    'cluster_checks_rebalancing_duration_seconds': 'cluster_checks.rebalancing_duration_seconds',
    'cluster_checks_successful_rebalancing_moves': 'cluster_checks.successful_rebalancing_moves',
    'cluster_checks_updating_stats_duration_seconds': 'cluster_checks.updating_stats_duration_seconds',
    'external_metrics_delay_seconds': 'external_metrics.delay_seconds',
    'external_metrics_processed_value': 'external_metrics.processed_value',
    'rate_limit_queries_limit': 'datadog.rate_limit_queries.limit',
    'rate_limit_queries_period': 'datadog.rate_limit_queries.period',
    'rate_limit_queries_remaining': 'datadog.rate_limit_queries.remaining',
    'rate_limit_queries_reset': 'datadog.rate_limit_queries.reset',
}


class DatadogClusterAgentCheck(OpenMetricsBaseCheck):
    """
    Collect Cluster Agent metrics from its Prometheus endpoint
    """

    def __init__(self, name, init_config, instances):
        default_namespace = 'datadog.cluster_agent'
        default_instances = {
            'datadog.cluster_agent': {
                'namespace': default_namespace,
                'metrics': [DEFAULT_METRICS],
                'label_joins': {
                    'leader_election_is_leader': {'labels_to_match': ['join_leader'], 'labels_to_get': ['is_leader']}
                },
            },
        }

        super(DatadogClusterAgentCheck, self).__init__(
            name, init_config, instances, default_namespace=default_namespace, default_instances=default_instances
        )
