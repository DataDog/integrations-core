# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.datadog_cluster_agent import DatadogClusterAgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

NAMESPACE = 'datadog.cluster_agent'
METRICS_WITH_LABEL_JOINS = [
    'cluster_checks.busyness',
    'cluster_checks.configs_dangling',
    'cluster_checks.configs_dispatched',
    'cluster_checks.nodes_reporting',
    'cluster_checks.rebalancing_decisions',
    'cluster_checks.rebalancing_duration_seconds',
    'cluster_checks.successful_rebalancing_moves',
    'cluster_checks.updating_stats_duration_seconds',
    'external_metrics.delay_seconds',
    'external_metrics.processed_value',
    'datadog.rate_limit_queries.limit',
    'datadog.rate_limit_queries.period',
    'datadog.rate_limit_queries.remaining',
    'datadog.rate_limit_queries.reset',
]

METRICS = [
    'admission_webhooks.certificate_expiry',
    'admission_webhooks.mutation_attempts',
    'admission_webhooks.reconcile_success',
    'admission_webhooks.webhooks_received',
]


def test_check(aggregator, instance, mock_get):
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance])

    # dry run to build mapping for label joins
    check.check(instance)

    # actual run that submits metrics
    check.check(instance)

    for metric in METRICS + METRICS_WITH_LABEL_JOINS:
        aggregator.assert_metric(NAMESPACE + '.' + metric)

    for metric in METRICS_WITH_LABEL_JOINS:
        aggregator.assert_metric_has_tag(NAMESPACE + '.' + metric, 'is_leader:true')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_metric_type=False)
