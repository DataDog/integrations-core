# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import pytest

from datadog_checks.airflow import AirflowCheck
from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectTimeoutError, HTTPClientReadTimeoutError

from . import common


def test_service_checks_cannot_connect(aggregator):
    check = AirflowCheck('airflow', {}, [common.INSTANCE_WRONG_URL])
    check.check(None)

    tags = ['key:my-tag', 'url:http://localhost:5555']

    aggregator.assert_service_check('airflow.can_connect', AgentCheck.CRITICAL, tags=tags, count=1)
    aggregator.assert_metric('airflow.can_connect', 0, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'error_type, expected_warning',
    [
        pytest.param(
            HTTPClientConnectTimeoutError,
            "Couldn't connect to URL: %s with exception: %s. Please verify the address is reachable",
            id='connect-timeout',
        ),
        pytest.param(
            HTTPClientReadTimeoutError,
            "Connection timeout when connecting to %s: %s",
            id='read-timeout',
        ),
    ],
)
def test_get_json_timeout_warning(fake_http, error_type, expected_warning):
    check = AirflowCheck('airflow', common.FULL_CONFIG, common.FULL_CONFIG['instances'])
    error = error_type('timed out')
    fake_http.register_response('GET', 'http://localhost:8080/api', error)

    with mock.patch.object(check, 'warning') as warning:
        assert check._get_json('http://localhost:8080/api') is None

    warning.assert_called_once_with(expected_warning, 'http://localhost:8080/api', error)


@pytest.mark.parametrize(
    'json_resp, expected_healthy_status, expected_healthy_value',
    [({'status': 'OK'}, AgentCheck.OK, 1), ({'status': 'KO'}, AgentCheck.CRITICAL, 0), ({}, AgentCheck.CRITICAL, 0)],
)
def test_service_checks_healthy_exp(
    aggregator, fake_http_response, json_resp, expected_healthy_status, expected_healthy_value
):
    instance = common.FULL_CONFIG['instances'][0]
    check = AirflowCheck('airflow', common.FULL_CONFIG, [instance])

    fake_http_response(f"{instance['url']}/api/experimental/test", json_data=json_resp)

    with mock.patch('datadog_checks.airflow.airflow.AirflowCheck._get_version', return_value=None):
        check.check(None)

    tags = ['key:my-tag', 'url:http://localhost:8080']

    aggregator.assert_service_check('airflow.healthy', expected_healthy_status, tags=tags, count=1)
    aggregator.assert_metric('airflow.healthy', expected_healthy_value, tags=tags, count=1)


@pytest.mark.parametrize(
    'metadb_status, scheduler_status, expected_healthy_status, expected_healthy_value',
    [
        ('healthy', 'healthy', AgentCheck.OK, 1),
        ('unhealthy', 'healthy', AgentCheck.CRITICAL, 0),
        ('healthy', 'unhealthy', AgentCheck.CRITICAL, 0),
    ],
)
def test_service_checks_healthy_stable(
    aggregator, fake_http_response, metadb_status, scheduler_status, expected_healthy_status, expected_healthy_value
):  # Stable is only defined in the context of Airflow 2
    instance = common.FULL_CONFIG['instances'][0]
    check = AirflowCheck('airflow', common.FULL_CONFIG, [instance])

    fake_http_response(
        f"{instance['url']}/api/v1/health",
        json_data={'metadatabase': {'status': metadb_status}, 'scheduler': {'status': scheduler_status}},
    )
    fake_http_response(
        f"{instance['url']}/api/v1/dags/~/dagRuns/~/taskInstances?state=running",
        json_data={'status': 'OK'},
    )

    with mock.patch('datadog_checks.airflow.airflow.AirflowCheck._get_version', return_value='2.6.2'):
        check.check(None)

    tags = ['key:my-tag', 'url:http://localhost:8080']

    aggregator.assert_service_check('airflow.healthy', expected_healthy_status, tags=tags, count=1)
    aggregator.assert_metric('airflow.healthy', expected_healthy_value, tags=tags, count=1)


def test_dag_total_tasks(aggregator, fake_http_response, task_instance):
    instance = common.FULL_CONFIG['instances'][0]
    check = AirflowCheck('airflow', common.FULL_CONFIG, [instance])

    fake_http_response(
        f"{instance['url']}/api/v1/health",
        json_data={'metadatabase': {'status': 'healthy'}, 'scheduler': {'status': 'healthy'}},
    )
    fake_http_response(
        f"{instance['url']}/api/v1/dags/~/dagRuns/~/taskInstances?state=running",
        json_data=task_instance,
    )

    with mock.patch('datadog_checks.airflow.airflow.AirflowCheck._get_version', return_value='2.6.2'):
        check.check(None)

    aggregator.assert_metric('airflow.dag.task.total_running', value=1, count=1)


def test_dag_task_ongoing_duration(aggregator, fake_http_response, task_instance):
    instance = common.FULL_CONFIG['instances'][0]
    check = AirflowCheck('airflow', common.FULL_CONFIG, [instance])

    fake_http_response(
        f"{instance['url']}/api/v1/health",
        json_data={'metadatabase': {'status': 'healthy'}, 'scheduler': {'status': 'healthy'}},
    )

    with mock.patch('datadog_checks.airflow.airflow.AirflowCheck._get_version', return_value='2.6.2'):
        with mock.patch(
            'datadog_checks.airflow.airflow.AirflowCheck._get_all_task_instances',
            return_value=task_instance.get('task_instances'),
        ):
            check.check(None)

    aggregator.assert_metric(
        'airflow.dag.task.ongoing_duration',
        tags=['key:my-tag', 'url:http://localhost:8080', 'dag_id:tutorial', 'task_id:sleep'],
        count=1,
    )


@pytest.mark.parametrize(
    "collect_ongoing_duration, should_call_method",
    [
        pytest.param(
            True,
            [
                mock.call(
                    'http://localhost:8080/api/v1/dags/~/dagRuns/~/taskInstances?state=running',
                    ['url:http://localhost:8080', 'key:my-tag'],
                )
            ],
            id="collect",
        ),
        pytest.param(
            False,
            [],
            id="don't collect",
        ),
    ],
)
def test_config_collect_ongoing_duration(fake_http_response, collect_ongoing_duration, should_call_method):
    instance = {**common.FULL_CONFIG['instances'][0], 'collect_ongoing_duration': collect_ongoing_duration}
    check = AirflowCheck('airflow', common.FULL_CONFIG, [instance])

    fake_http_response(
        f"{instance['url']}/api/v1/health",
        json_data={'metadatabase': {'status': 'healthy'}, 'scheduler': {'status': 'healthy'}},
    )

    with mock.patch('datadog_checks.airflow.airflow.AirflowCheck._get_version', return_value='2.6.2'):
        with mock.patch(
            'datadog_checks.airflow.airflow.AirflowCheck._get_all_task_instances'
        ) as mock_get_all_task_instances:
            check.check(None)

            # Assert method calls
            mock_get_all_task_instances.assert_has_calls(should_call_method, any_order=False)
