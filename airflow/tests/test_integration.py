# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.airflow import AirflowCheck
from datadog_checks.base import AgentCheck

from . import common


@pytest.mark.usefixtures('dd_environment')
def test_service_checks_integration(aggregator, dd_run_check):
    check = AirflowCheck('airflow', common.FULL_CONFIG, [common.INSTANCE])
    dd_run_check(check)

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
