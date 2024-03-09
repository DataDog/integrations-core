# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import PY2
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.datadog_cluster_agent import DatadogClusterAgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

NAMESPACE = 'datadog.cluster_agent'

METRICS = [
    'admission_webhooks.certificate_expiry',
    'admission_webhooks.library_injection_attempts',
    'admission_webhooks.library_injection_errors',
    'admission_webhooks.mutation_attempts',
    'admission_webhooks.mutation_errors',
    'admission_webhooks.patcher.attempts',
    'admission_webhooks.patcher.completed',
    'admission_webhooks.patcher.errors',
    'admission_webhooks.rc_provider.configs',
    'admission_webhooks.rc_provider.invalid_configs',
    'admission_webhooks.reconcile_errors',
    'admission_webhooks.reconcile_success',
    'admission_webhooks.response_duration.count',
    'admission_webhooks.response_duration.sum',
    'admission_webhooks.webhooks_received',
    'aggregator.flush',
    'aggregator.processed',
    'api_requests',
    'autodiscovery.errors',
    'autodiscovery.poll_duration.count',
    'autodiscovery.poll_duration.sum',
    'autodiscovery.watched_resources',
    'cluster_checks.busyness',
    'cluster_checks.configs_dangling',
    'cluster_checks.configs_dispatched',
    'cluster_checks.configs_info',
    'cluster_checks.failed_stats_collection',
    'cluster_checks.nodes_reporting',
    'cluster_checks.rebalancing_decisions',
    'cluster_checks.rebalancing_duration_seconds',
    'cluster_checks.successful_rebalancing_moves',
    'cluster_checks.updating_stats_duration_seconds',
    'datadog.rate_limit_queries.limit',
    'datadog.rate_limit_queries.period',
    'datadog.rate_limit_queries.remaining',
    'datadog.rate_limit_queries.remaining_min',
    'datadog.rate_limit_queries.reset',
    'datadog.requests',
    'endpoint_checks.configs_dispatched',
    'external_metrics',
    'external_metrics.api_elapsed.count',
    'external_metrics.api_elapsed.sum',
    'external_metrics.api_requests',
    'external_metrics.datadog_metrics',
    'external_metrics.delay_seconds',
    'external_metrics.processed_value',
    'go.goroutines',
    'go.memstats.alloc_bytes',
    'go.threads',
    'kubernetes_apiserver.emitted_events',
    'kubernetes_apiserver.kube_events',
    'language_detection_dca_handler.processed_requests',
    'language_detection_patcher.patches',
    'secret_backend.elapsed',
]

METRICS_V2 = [
    'admission_webhooks.certificate_expiry',
    'admission_webhooks.library_injection_attempts.count',
    'admission_webhooks.library_injection_errors.count',
    'admission_webhooks.mutation_attempts',
    'admission_webhooks.mutation_errors',
    'admission_webhooks.patcher.attempts.count',
    'admission_webhooks.patcher.completed.count',
    'admission_webhooks.patcher.errors.count',
    'admission_webhooks.rc_provider.configs',
    'admission_webhooks.rc_provider.invalid_configs',
    'admission_webhooks.reconcile_errors',
    'admission_webhooks.reconcile_success',
    'admission_webhooks.webhooks_received',
    'aggregator.flush.count',
    'aggregator.processed.count',
    'api_requests.count',
    'autodiscovery.errors',
    'autodiscovery.watched_resources',
    'cluster_checks.busyness',
    'cluster_checks.configs_dangling',
    'cluster_checks.configs_dispatched',
    'cluster_checks.configs_info',
    'cluster_checks.failed_stats_collection.count',
    'cluster_checks.nodes_reporting',
    'cluster_checks.rebalancing_decisions.count',
    'cluster_checks.rebalancing_duration_seconds',
    'cluster_checks.successful_rebalancing_moves.count',
    'cluster_checks.updating_stats_duration_seconds',
    'datadog.rate_limit_queries.limit',
    'datadog.rate_limit_queries.period',
    'datadog.rate_limit_queries.remaining',
    'datadog.rate_limit_queries.remaining_min',
    'datadog.rate_limit_queries.reset',
    'datadog.requests.count',
    'endpoint_checks.configs_dispatched',
    'external_metrics',
    'external_metrics.api_requests',
    'external_metrics.datadog_metrics',
    'external_metrics.delay_seconds',
    'external_metrics.processed_value',
    'go.goroutines',
    'go.memstats.alloc_bytes',
    'go.threads',
    'kubernetes_apiserver.emitted_events.count',
    'kubernetes_apiserver.kube_events.count',
    'language_detection_dca_handler.processed_requests.count',
    'language_detection_patcher.patches.count',
    'secret_backend.elapsed',
]


def test_check(aggregator, dd_run_check, instance_v1, mock_metrics_endpoint):
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance_v1])

    # dry run to build mapping for label joins
    dd_run_check(check)
    dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(NAMESPACE + '.' + metric)
        aggregator.assert_metric_has_tag_prefix(NAMESPACE + '.' + metric, 'is_leader:')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_check_v2(aggregator, dd_run_check, instance_v2, mock_metrics_endpoint):
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance_v2])

    # dry run to build mapping for label joins
    dd_run_check(check)
    dd_run_check(check)

    for metric in METRICS_V2:
        aggregator.assert_metric(NAMESPACE + '.' + metric)
        aggregator.assert_metric_has_tag_prefix(NAMESPACE + '.' + metric, 'is_leader:')

    aggregator.assert_all_metrics_covered()
    # Can't use metadata metrics for now, as we default to v1 metrics
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())


# Minimal E2E testing
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception):
        dd_agent_check(instance, rate=True)
    tag = "endpoint:" + instance.get('prometheus_url')
    aggregator.assert_service_check("datadog.cluster_agent.prometheus.health", AgentCheck.CRITICAL, count=2, tags=[tag])
