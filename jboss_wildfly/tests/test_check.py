# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.jmx import JVM_E2E_METRICS, JVM_E2E_METRICS_NEW
from datadog_checks.dev.utils import get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)
    metrics = [
        'jboss.jdbc_connections.active',
        'jboss.jdbc_connections.count',
        'jboss.jdbc_connections.idle',
        'jboss.jdbc_connections.request_wait',
        'jboss.jdbc_preparedstatementcache.hit',
        'jboss.jdbc_preparedstatementcache.miss',
        'jboss.jdbc_preparedstatementcache.size',
        'jboss.jdbc_xacommit.count',
        'jboss.jdbc_xarecover.count',
        'jboss.jdbc_xarollback.count',
        'jboss.transactions.aborted',
        'jboss.transactions.application_rollbacks',
        'jboss.transactions.committed',
        'jboss.transactions.count',
        'jboss.transactions.heuristics',
        'jboss.transactions.inflight',
        'jboss.transactions.nested',
        'jboss.transactions.resource_rollbacks',
        'jboss.transactions.system_rollbacks',
        'jboss.transactions.timed_out',
        'jboss.undertow_listener.bytes_received',
        'jboss.undertow_listener.bytes_sent',
        'jboss.undertow_listener.error_count',
        'jboss.undertow_listener.processing_time',
        'jboss.undertow_listener.request_count',
    ] + JVM_E2E_METRICS
    metrics.remove('jvm.gc.cms.count')
    metrics.remove('jvm.gc.parnew.time')
    for metric in metrics:
        aggregator.assert_metric(metric)

    tags = ['instance:jboss_wildfly']
    aggregator.assert_service_check('jboss.can_connect', status=AgentCheck.OK, tags=tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW)
