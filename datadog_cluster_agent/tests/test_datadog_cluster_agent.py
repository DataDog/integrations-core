# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.datadog_cluster_agent import DatadogClusterAgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .conftest import mock_metrics_response

NAMESPACE = 'datadog.cluster_agent'

METRICS = [
    'admission_webhooks.certificate_expiry',
    'admission_webhooks.cws_exec_mutation_attempts',
    'admission_webhooks.cws_pod_mutation_attempts',
    'admission_webhooks.cws_response_duration.count',
    'admission_webhooks.cws_response_duration.sum',
    'admission_webhooks.library_injection_attempts',
    'admission_webhooks.library_injection_errors',
    'admission_webhooks.mutation_attempts',
    'admission_webhooks.validation_attempts',
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
    'admission_webhooks.image_resolution_attempts',
    'aggregator.flush',
    'aggregator.processed',
    'api_requests',
    'autodiscovery.errors',
    'autodiscovery.poll_duration.count',
    'autodiscovery.poll_duration.sum',
    'autodiscovery.watched_resources',
    'cluster_checks.busyness',
    'cluster_checks.configs_dangling',
    'cluster_checks.unscheduled_check',
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
    'instrumentation_controller.reconciliations',
    'instrumentation_controller.resources',
    'kubernetes_apiserver.emitted_events',
    'kubernetes_apiserver.kube_events',
    'language_detection_dca_handler.processed_requests',
    'language_detection_patcher.patches',
    'metadata_streaming.history_resyncs',
    'secret_backend.elapsed',
    'tagger.stored_entities',
    'tagger.updated_entities',
    'workloadmeta.events_received',
    'workloadmeta.notifications_sent',
    'workloadmeta.stored_entities',
    'workloadmeta.subscribers',
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

    aggregator.assert_metric(
        NAMESPACE + '.metadata_streaming.history_resyncs',
        value=3,
        metric_type=aggregator.COUNT,
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_leadership_changes_do_not_resend_counter_totals(aggregator, instance, metrics_text):
    # Regression test: a leader election changed `is_leader` on every count, and the Agent flushed each counter's
    # lifetime total as a single delta.
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance])
    as_follower = metrics_text.replace('is_leader="true"', 'is_leader="false"')

    with mock_metrics_response(as_follower):
        check.check(instance)
        check.check(instance)

    # Metrics listed before `leader_election_is_leader` pick up a new `is_leader` value one scrape later.
    for text, leader_tag in ((metrics_text, 'is_leader:true'), (as_follower, 'is_leader:false')):
        aggregator.reset()
        with mock_metrics_response(text):
            check.check(instance)
            check.check(instance)

        counts = [stub for name in aggregator.metric_names for stub in aggregator.metrics(name)]
        counts = [stub for stub in counts if stub.type == aggregator.COUNT]
        assert counts
        assert all(stub.value == 0 for stub in counts)
        aggregator.assert_metric(
            NAMESPACE + '.datadog.requests', value=0, tags=['join_leader:true', 'status:success', leader_tag]
        )


@pytest.mark.parametrize(
    'old_line, new_line, tags, expected',
    [
        pytest.param(
            'datadog_requests{join_leader="true",status="success"} 13006',
            'datadog_requests{join_leader="true",status="success"} 13010',
            ['status:success'],
            4,
            id='increase',
        ),
        pytest.param(
            'datadog_requests{join_leader="true",status="success"} 13006',
            'datadog_requests{join_leader="true",status="success"} 10',
            ['status:success'],
            10,
            id='reset',
        ),
        pytest.param(
            'datadog_requests{join_leader="true",status="success"} 13006',
            'datadog_requests{join_leader="true",status="success"} 13006\n'
            'datadog_requests{join_leader="true",status="new"} 5',
            ['status:new'],
            5,
            id='new series',
        ),
    ],
)
def test_counter_delta(aggregator, instance, metrics_text, old_line, new_line, tags, expected):
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance])
    with mock_metrics_response(metrics_text):
        check.check(instance)
        check.check(instance)
    aggregator.reset()

    with mock_metrics_response(metrics_text.replace(old_line, new_line)):
        check.check(instance)

    aggregator.assert_metric(
        NAMESPACE + '.datadog.requests',
        value=expected,
        tags=['is_leader:true', 'join_leader:true'] + tags,
        metric_type=aggregator.COUNT,
    )


# Minimal E2E testing
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception):
        dd_agent_check(instance, rate=True)
    tag = "endpoint:" + instance.get('prometheus_url')
    aggregator.assert_service_check("datadog.cluster_agent.prometheus.health", AgentCheck.CRITICAL, count=2, tags=[tag])
