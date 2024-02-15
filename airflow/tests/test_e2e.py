# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

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
