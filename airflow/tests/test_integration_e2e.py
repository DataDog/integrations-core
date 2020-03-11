# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.airflow import AirflowCheck
from datadog_checks.base import AgentCheck

from . import common


@pytest.mark.usefixtures('dd_environment')
def test_service_checks_integration(aggregator):
    check = AirflowCheck('airflow', common.FULL_CONFIG, [common.INSTANCE])
    check.check(common.INSTANCE)

    assert_service_checks(aggregator)


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

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata()
