# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.airflow import AirflowCheck
from datadog_checks.base import AgentCheck
from datadog_checks.dev.docker import CONTAINER_STABILITY_LOG_PATTERNS, assert_all_discovery_candidates_stable

from . import common


@pytest.mark.e2e
def test_service_checks_e2e(dd_agent_check):
    aggregator = dd_agent_check(common.FULL_CONFIG)

    assert_service_checks(aggregator)


def assert_service_checks(aggregator):
    tags = ['key:my-tag', 'url:http://localhost:8080']

    aggregator.assert_service_check('airflow.can_connect', AgentCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('airflow.can_connect', 1, tags=tags, count=1)

    aggregator.assert_service_check('airflow.healthy', AgentCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('airflow.healthy', 1, tags=tags, count=1)

    aggregator.assert_metric('airflow.dag.task.total_running', tags=tags, count=1)
    aggregator.assert_metric(
        'airflow.dag.task.ongoing_duration',
        count=0,
    )

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery()

    # discovery can't know the custom `tags` or the exact discovered `url` ahead of time, so tags aren't asserted here
    aggregator.assert_service_check('airflow.can_connect', AgentCheck.OK, count=1)
    aggregator.assert_metric('airflow.can_connect', 1, count=1)

    aggregator.assert_service_check('airflow.healthy', AgentCheck.OK, count=1)
    aggregator.assert_metric('airflow.healthy', 1, count=1)

    # discovery has no way to supply the `username`/`password` the task-instances endpoint requires, so that request
    # gets a 401 and `airflow.dag.task.total_running`/`ongoing_duration` are never submitted for a discovered instance
    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    # Airflow's own admin/RBAC bootstrap logs permission views named e.g. "can read on ImportError", which trips the
    # generic `error` pattern even though nothing is actually failing; keep only the crash-indicating patterns.
    log_patterns = [pattern for pattern in CONTAINER_STABILITY_LOG_PATTERNS if pattern != r'error']
    assert_all_discovery_candidates_stable(
        dd_agent_check, AirflowCheck, compose_service='server', log_patterns=log_patterns
    )
