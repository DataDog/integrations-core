# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.datadog_cluster_agent import DatadogClusterAgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

NAMESPACE = 'datadog.cluster_agent'

METRICS = [
    'admission_webhooks.certificate_expiry',
    'admission_webhooks.mutation_attempts',
    'admission_webhooks.mutation_errors',
    'admission_webhooks.reconcile_errors',
    'admission_webhooks.reconcile_success',
    'admission_webhooks.webhooks_received',
    'admission_webhooks.library_injection_attempts',
    'admission_webhooks.library_injection_errors',
    'admission_webhooks.patcher.attempts',
    'admission_webhooks.patcher.completed',
    'admission_webhooks.patcher.errors',
    'admission_webhooks.rc_provider.configs',
    'admission_webhooks.rc_provider.invalid_configs',
    'aggregator.flush',
    'aggregator.processed',
    'api_requests',
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
    'datadog.rate_limit_queries.reset',
    'datadog.requests',
    'external_metrics',
    'external_metrics.datadog_metrics',
    'external_metrics.delay_seconds',
    'external_metrics.processed_value',
    'secret_backend.elapsed',
    'go.goroutines',
    'go.memstats.alloc_bytes',
    'go.threads',
    'endpoint_checks.configs_dispatched',
    'autodiscovery.poll_duration.count',
    'autodiscovery.poll_duration.sum',
    'autodiscovery.watched_resources',
    'autodiscovery.errors',
    'kubernetes_apiserver.kube_events',
    'kubernetes_apiserver.emitted_events',
]


def test_check(aggregator, instance, mock_metrics_endpoint):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance])

    # dry run to build mapping for label joins
    check.check(instance)

    check.check(instance)

    for metric in METRICS:
        aggregator.assert_metric(NAMESPACE + '.' + metric)
        aggregator.assert_metric_has_tag_prefix(NAMESPACE + '.' + metric, 'is_leader:')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


# Minimal E2E testing
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception):
        dd_agent_check(instance, rate=True)
    tag = "endpoint:" + instance.get('prometheus_url')
    aggregator.assert_service_check("datadog.cluster_agent.prometheus.health", AgentCheck.CRITICAL, count=2, tags=[tag])
