# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.airflow import AirflowCheck
from datadog_checks.base import AgentCheck
from .common import URL

INSTANCE = {'url': URL, 'tags': ['key:my-tag']}

CONFIG = {
    'instances': [INSTANCE],
    'init_config': {},
}


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_checks_integration(aggregator):
    check = AirflowCheck('airflow', CONFIG, [INSTANCE])
    check.check(INSTANCE)

    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_service_checks_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG, times=3)

    assert_service_checks(aggregator)


def assert_service_checks(aggregator):
    tags = ['key:my-tag', 'url:http://localhost:8080/api/experimental/test']
    aggregator.assert_service_check('airflow.can_connect', AgentCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('airflow.can_connect', 1, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()
