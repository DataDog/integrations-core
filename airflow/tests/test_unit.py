# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import pytest

from datadog_checks.airflow import AirflowCheck
from datadog_checks.base import AgentCheck

from . import common


def test_service_checks_cannot_connect(aggregator):
    check = AirflowCheck('airflow', {}, [common.INSTANCE_WRONG_URL])
    check.check(None)

    tags = ['key:my-tag', 'url:http://localhost:5555']

    aggregator.assert_service_check('airflow.can_connect', AgentCheck.CRITICAL, tags=tags, count=1)
    aggregator.assert_metric('airflow.can_connect', 0, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'json_resp, expected_healthy_status, expected_healthy_value',
    [({'status': 'OK'}, AgentCheck.OK, 1), ({'status': 'KO'}, AgentCheck.CRITICAL, 0), ({}, AgentCheck.CRITICAL, 0)],
)
def test_service_checks_healthy(aggregator, json_resp, expected_healthy_status, expected_healthy_value):
    instance = common.FULL_CONFIG['instances'][0]
    check = AirflowCheck('airflow', common.FULL_CONFIG, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.json.return_value = json_resp
        req.get.return_value = mock_resp

        check.check(None)

    tags = ['key:my-tag', 'url:http://localhost:8080']

    aggregator.assert_service_check('airflow.healthy', expected_healthy_status, tags=tags, count=1)
    aggregator.assert_metric('airflow.healthy', expected_healthy_value, tags=tags, count=1)
