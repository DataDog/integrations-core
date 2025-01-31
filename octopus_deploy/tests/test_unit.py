# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.octopus_deploy import OctopusDeployCheck

from .constants import (
    ALL_DEPLOYMENT_LOGS,
    ALL_EVENTS,
    ALL_METRICS,
    COMPLETED_METRICS,
    DEPLOY_METRICS,
    ENV_METRICS,
    MOCKED_TIME1,
    MOCKED_TIME2,
    ONLY_TEST_LOGS,
    PROJECT_METRICS,
)


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_exception', 'can_connect'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api/spaces': MockResponse(status_code=500),
                }
            },
            pytest.raises(Exception, match=r'Could not connect to octopus API.*'),
            0,
            id='http error',
        ),
        pytest.param(
            {
                'mock_data': {
                    '/api/spaces': {"Items": []},
                }
            },
            does_not_raise(),
            1,
            id='http ok',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_can_connect(get_current_datetime, dd_run_check, aggregator, expected_exception, can_connect):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    with expected_exception:
        dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.api.can_connect', can_connect)


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_all_metrics_covered(
    get_current_datetime,
    dd_run_check,
    aggregator,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.api.can_connect', 1)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {
                'mock_data': {
                    '/api/spaces': {"Items": []},
                }
            },
            id='empty spaces',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_empty_spaces(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.space.count', count=0)


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_one_space(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.space.count',
        1,
        tags=['octopus_server:http://localhost:80', 'space_id:Spaces-1', 'space_name:Default'],
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_project_groups(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-1',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-2',
            'project_group_name:test-group',
            'space_name:Default',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-3',
            'project_group_name:hello',
            'space_name:Default',
        ],
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_projects(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.project.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_id:Projects-1',
            'project_name:test-api',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_id:Projects-2',
            'project_name:my-project',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_id:Projects-3',
            'project_name:test',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_id:Projects-4',
            'project_name:hi',
            'project_group_name:test-group',
            'space_name:Default',
        ],
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_queued_or_running_tasks(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        30,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        150,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'release_version:0.0.2',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing',
        1,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'deployment_id:Deployments-18',
            'release_version:0.0.1',
            'environment_name:staging',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued',
        0,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'deployment_id:Deployments-18',
            'release_version:0.0.1',
            'environment_name:staging',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.waiting',
        1,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'deployment_id:Deployments-18',
            'release_version:0.0.1',
            'environment_name:staging',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'release_version:0.0.2',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        60,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-19',
            'release_version:0.0.2',
            'environment_name:dev',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-19',
            'release_version:0.0.2',
            'environment_name:dev',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-19',
            'release_version:0.0.2',
            'environment_name:dev',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing',
        0,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'deployment_id:Deployments-19',
            'release_version:0.0.2',
            'environment_name:dev',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued',
        1,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'deployment_id:Deployments-19',
            'release_version:0.0.2',
            'environment_name:dev',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.waiting',
        0,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'deployment_id:Deployments-19',
            'release_version:0.0.2',
            'environment_name:dev',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
        ],
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_completed_tasks(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
            'release_version:0.0.2',
            'environment_name:dev',
            'deployment_id:Deployments-19',
            'task_state:Queued',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'project_name:my-project',
            'server_node:OctopusServerNodes-50c3dfbarc82',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'task_state:Executing',
        ],
        count=1,
    )
    deployment_metrics = aggregator.metrics('octopus_deploy.deployment.count')
    assert len(deployment_metrics) == 2

    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:0.0.2',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        110,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:0.0.2',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        50,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:0.0.2',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        5,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'release_version:0.0.2',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        90,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        54,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'release_version:0.0.1',
            'environment_name:staging',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        18,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        41,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        14,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {
                'mock_data': {
                    '/api/spaces': {
                        "Items": [
                            {
                                "Id": "Spaces-1",
                                "Name": "First",
                            },
                            {
                                "Id": "Spaces-2",
                                "Name": "Second",
                            },
                        ]
                    },
                    '/api/Spaces-1/projectgroups': {"Items": []},
                    '/api/Spaces-2/projectgroups': {"Items": []},
                }
            },
            id='empty spaces',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_discovery_spaces(get_current_datetime, dd_run_check, aggregator):
    instance = {
        'octopus_endpoint': 'http://localhost:80',
        'spaces': {
            'include': ['Second'],
        },
    }
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.space.count',
        tags=['octopus_server:http://localhost:80', 'space_name:Default', 'space_name:First'],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.space.count',
        tags=['octopus_server:http://localhost:80', 'space_id:Spaces-2', 'space_name:Second'],
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_discovery_default_project_groups(get_current_datetime, dd_run_check, aggregator):
    instance = {
        'octopus_endpoint': 'http://localhost:80',
        'project_groups': {
            'include': ['hello'],
        },
    }
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-1',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-2',
            'project_group_name:test-group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-3',
            'project_group_name:hello',
            'space_name:Default',
        ],
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_discovery_space_project_groups(get_current_datetime, dd_run_check, aggregator):
    instance = {
        'octopus_endpoint': 'http://localhost:80',
        'spaces': {
            'include': [
                {
                    'Default': {
                        'project_groups': {
                            'include': ['hello'],
                        }
                    }
                }
            ],
        },
    }
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-1',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-2',
            'project_group_name:test-group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-3',
            'project_group_name:hello',
            'space_name:Default',
        ],
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_discovery_default_projects(get_current_datetime, dd_run_check, aggregator):
    instance = {
        'octopus_endpoint': 'http://localhost:80',
        'projects': {
            'include': ['test-api'],
        },
    }
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.project.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_id:Projects-1',
            'project_name:test-api',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_id:Projects-2',
            'project_name:my-project',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_name:test',
            'project_name:test',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_id:Projects-4',
            'project_name:hi',
            'project_group_name:test-group',
            'space_name:Default',
        ],
        count=0,
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_discovery_space_project_group_projects(get_current_datetime, dd_run_check, aggregator):
    instance = {
        'octopus_endpoint': 'http://localhost:80',
        'spaces': {
            'include': [
                {
                    'Default': {
                        'project_groups': {
                            'include': [
                                {
                                    'hello': {
                                        'projects': {
                                            'include': ['.*'],
                                        },
                                    }
                                }
                            ],
                        },
                    }
                }
            ],
        },
    }
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-1',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-2',
            'project_group_name:test-group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'project_group_id:ProjectGroups-3',
            'project_group_name:hello',
            'space_name:Default',
        ],
    )


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            {
                'octopus_endpoint': 'http://localhost:80',
                'spaces': {
                    'include': ['Default'],
                },
                'project_groups': {
                    'include': ['Default Project Group'],
                },
                'projects': {
                    'include': ['.*'],
                },
            },
            id='all default',
        ),
        pytest.param(
            {
                'octopus_endpoint': 'http://localhost:80',
                'spaces': {
                    'include': [
                        {
                            'Default': {
                                'project_groups': {
                                    'include': ['Default Project Group'],
                                },
                            }
                        }
                    ],
                },
                'projects': {
                    'include': ['.*'],
                },
            },
            id='with project groups',
        ),
        pytest.param(
            {
                'octopus_endpoint': 'http://localhost:80',
                'spaces': {
                    'include': [
                        {
                            'Default': {
                                'project_groups': {
                                    'include': [
                                        {
                                            'Default Project Group': {
                                                'projects': {
                                                    'include': ['.*'],
                                                },
                                            }
                                        }
                                    ],
                                },
                            }
                        }
                    ],
                },
            },
            id='with projects',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_run_twice(get_current_datetime, dd_run_check, aggregator, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.space.count')
    aggregator.assert_metric('octopus_deploy.project_group.count')
    aggregator.assert_metric('octopus_deploy.project.count')

    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.space.count')
    aggregator.assert_metric('octopus_deploy.project_group.count')
    aggregator.assert_metric('octopus_deploy.project.count')


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_empty_include(get_current_datetime, dd_run_check, aggregator):
    instance = {
        'octopus_endpoint': 'http://localhost:80',
        'spaces': {
            'include': [],
        },
    }
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.space.count', count=0)


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_log'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api/Spaces-1/tasks': MockResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/tasks: 500 Server Error: None for url: None',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_tasks_endpoint_unavailable(get_current_datetime, dd_run_check, expected_log, caplog):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.WARNING)
    dd_run_check(check)
    assert expected_log in caplog.text


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_server_node_metrics(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    aggregator.assert_metric(
        "octopus_deploy.server_node.count",
        1,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.max_concurrent_tasks",
        5,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.in_maintenance_mode",
        0,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_log'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api/octopusservernodes': MockResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/octopusservernodes: 500 Server Error: None for url: None',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_server_node_endpoint_failed(get_current_datetime, dd_run_check, aggregator, expected_log, caplog):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.WARNING)
    dd_run_check(check)
    assert expected_log in caplog.text
    aggregator.assert_metric(
        "octopus_deploy.server_node.count",
        1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.max_concurrent_tasks",
        5,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.in_maintenance_mode",
        5,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )


@pytest.mark.parametrize(
    ('logs_enabled, project_groups, expected_logs'),
    [
        pytest.param(True, None, ALL_DEPLOYMENT_LOGS, id='logs enabled'),
        pytest.param(False, None, [], id='logs disabled'),
        pytest.param(
            True,
            {'include': [{'.*': {'projects': {'include': [r'^test$']}}}]},
            ONLY_TEST_LOGS,
            id='logs enabled only test logs',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_deployment_logs(
    get_current_datetime,
    datadog_agent,
    dd_run_check,
    instance,
    logs_enabled,
    project_groups,
    expected_logs,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['project_groups'] = project_groups
    datadog_agent._config['logs_enabled'] = logs_enabled
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    datadog_agent.assert_logs(check.check_id, [])
    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)
    datadog_agent.assert_logs(check.check_id, expected_logs)


@pytest.mark.parametrize(
    ('expected_events', 'events_enabled'),
    [pytest.param([], False, id='events disabled'), pytest.param(ALL_EVENTS, True, id='events enabled')],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_events(get_current_datetime, dd_run_check, aggregator, expected_events, events_enabled):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['collect_events'] = events_enabled
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)
    for event in expected_events:
        aggregator.assert_event(event['message'], tags=event['tags'], count=1)


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_environment_metrics(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=1,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_environments_discovery_one_include(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80', 'environments': {'include': ['dev']}}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
        count=0,
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
        count=0,
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=1,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
        count=0,
    )

    aggregator.assert_metric_has_tag("octopus_deploy.deployment.count", 'environment_name:dev')
    aggregator.assert_metric_has_tag("octopus_deploy.deployment.count", 'environment_name:staging', count=0)


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_environments_discovery_exclude_dev(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80', 'environments': {'exclude': ['dev'], 'include': ['.*']}}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )
    aggregator.assert_metric_has_tag("octopus_deploy.deployment.count", 'environment_name:dev', count=0)
    aggregator.assert_metric_has_tag("octopus_deploy.deployment.count", 'environment_name:staging')


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_environments_discovery_include_invalid(get_current_datetime, dd_run_check, aggregator):
    instance = {'octopus_endpoint': 'http://localhost:80', 'environments': {'include': ['test']}}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    env_metrics = aggregator.metrics('octopus_deploy.environment.count')
    assert len(env_metrics) == 0
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )
    aggregator.assert_metric_has_tag("octopus_deploy.deployment.count", 'environment_name:dev', count=0)
    aggregator.assert_metric_has_tag("octopus_deploy.deployment.count", 'environment_name:staging', count=0)


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_log'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api/Spaces-1/environments': MockResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/environments: 500 Server Error: None for url: None',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_environments_metrics_http_failure(get_current_datetime, dd_run_check, aggregator, expected_log, caplog):
    instance = {'octopus_endpoint': 'http://localhost:80', 'environments': {'include': ['test']}}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.WARNING)
    dd_run_check(check)
    env_metrics = aggregator.metrics('octopus_deploy.environment.count')
    assert len(env_metrics) == 0
    assert expected_log in caplog.text
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.count',
        value=1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.use_guided_failure',
        value=0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )

    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=1,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:dev',
            'environment_slug:dev',
            'environment_id:Environments-1',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.environment.allow_dynamic_infrastructure',
        value=0,
        count=0,
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'environment_name:staging',
            'environment_slug:staging',
            'environment_id:Environments-2',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_log'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api/Spaces-1/releases/Releases-3': MockResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/releases/Releases-3: 500 Server Error: None for url: None',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_deployment_metrics_releases_http_failure(get_current_datetime, dd_run_check, aggregator, expected_log, caplog):
    instance = {'octopus_endpoint': 'http://localhost:80'}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
            'release_version:None',
            'environment_name:dev',
            'deployment_id:Deployments-19',
            'task_state:Queued',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'project_name:my-project',
            'server_node:OctopusServerNodes-50c3dfbarc82',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'task_state:Executing',
        ],
        count=1,
    )
    deployment_metrics = aggregator.metrics('octopus_deploy.deployment.count')
    assert len(deployment_metrics) == 2
    assert expected_log in caplog.text
    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:None',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        110,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:None',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        50,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:None',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        5,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'release_version:None',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        90,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        54,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'release_version:0.0.1',
            'environment_name:staging',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:staging',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        18,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        41,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        14,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_log'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api/Spaces-1/deployments/Deployments-18': MockResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/deployments/Deployments-18: 500 Server Error: None for url: None',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_deployment_metrics_deployments_http_failure(
    get_current_datetime, dd_run_check, aggregator, expected_log, caplog
):
    instance = {'octopus_endpoint': 'http://localhost:80'}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
            'release_version:0.0.2',
            'environment_name:dev',
            'deployment_id:Deployments-19',
            'task_state:Queued',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'space_name:Default',
            'project_name:my-project',
            'server_node:OctopusServerNodes-50c3dfbarc82',
            'deployment_id:Deployments-18',
            'environment_name:None',
            'release_version:None',
            'task_state:Executing',
        ],
        count=0,
    )
    deployment_metrics = aggregator.metrics('octopus_deploy.deployment.count')
    assert len(deployment_metrics) == 1
    assert expected_log in caplog.text
    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:0.0.2',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        110,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:0.0.2',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        50,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'release_version:0.0.2',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        5,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-19',
            'environment_name:dev',
            'release_version:0.0.2',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:None',
            'release_version:None',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        90,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:None',
            'release_version:None',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        54,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'release_version:None',
            'environment_name:None',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        1,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-18',
            'environment_name:None',
            'release_version:None',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        18,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        41,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        14,
        tags=[
            'octopus_server:http://localhost:80',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'deployment_id:Deployments-17',
            'environment_name:dev',
            'release_version:0.0.1',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_log'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api/Spaces-1/environments': MockResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/environments: 500 Server Error: None for url: None',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_deployment_metrics_environments_http_failure(
    get_current_datetime, dd_run_check, aggregator, expected_log, caplog
):
    instance = {'octopus_endpoint': 'http://localhost:80', 'environments': {'include': ['test']}}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.WARNING)
    dd_run_check(check)
    assert expected_log in caplog.text
    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)

    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        count=0,
    )


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_deployments_caching(get_current_datetime, dd_run_check, mock_http_get):
    instance = {'octopus_endpoint': 'http://localhost:80'}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)

    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)

    assert args_list.count('http://localhost:80/api/Spaces-1/releases/Releases-1') == 1
    assert args_list.count('http://localhost:80/api/Spaces-1/releases/Releases-2') == 1
    assert args_list.count('http://localhost:80/api/Spaces-1/releases/Releases-3') == 1

    assert args_list.count('http://localhost:80/api/Spaces-1/deployments/Deployments-17') == 1
    assert args_list.count('http://localhost:80/api/Spaces-1/deployments/Deployments-18') == 1
    assert args_list.count('http://localhost:80/api/Spaces-1/deployments/Deployments-19') == 1

    assert args_list.count('http://localhost:80/api/Spaces-1/environments') == 5


@pytest.mark.parametrize(
    ('paginated_limit'),
    [pytest.param(30, id='high limit'), pytest.param(2, id='low limit')],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_octopusservernodes(
    get_current_datetime, dd_run_check, aggregator, paginated_limit, mock_http_get
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
        args, kwargs = call
        take = kwargs.get('params', {}).get('take')
        skip = kwargs.get('params', {}).get('skip')
        args_list += [(args[0], take, skip)]

    assert args_list.count(('http://localhost:80/api/octopusservernodes', paginated_limit, 0)) == 1

    aggregator.assert_metric(
        "octopus_deploy.server_node.count",
        1,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.max_concurrent_tasks",
        5,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.in_maintenance_mode",
        0,
        count=1,
        tags=[
            'octopus_server:http://localhost:80',
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )


@pytest.mark.parametrize(
    ('paginated_limit, expected_skip_take_args'),
    [
        pytest.param(
            30,
            [
                (['http://localhost:80/api/Spaces-1/events'], 0, 30),
                (['http://localhost:80/api/Spaces-1/events'], 0, 30),
            ],
            id='high limit',
        ),
        pytest.param(
            2,
            [
                (['http://localhost:80/api/Spaces-1/events'], 0, 2),
                (['http://localhost:80/api/Spaces-1/events'], 0, 2),
                (['http://localhost:80/api/Spaces-1/events'], 2, 2),
            ],
            id='low limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_events(
    get_current_datetime,
    dd_run_check,
    aggregator,
    paginated_limit,
    mock_http_get,
    expected_skip_take_args,
    caplog,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['paginated_limit'] = paginated_limit
    instance['collect_events'] = True

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)

    skip_take_args = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        take = kwargs.get('params', {}).get('take')
        skip = kwargs.get('params', {}).get('skip')
        if 'events' in args[0]:
            print(kwargs)
            skip_take_args += [(list(args), skip, take)]

    assert skip_take_args == expected_skip_take_args

    for event in ALL_EVENTS:
        aggregator.assert_event(event['message'], tags=event['tags'], count=1)


@pytest.mark.parametrize(
    ('paginated_limit, expected_skip_take_args'),
    [
        pytest.param(
            30,
            [
                (['http://localhost:80/api/spaces'], 0, 30),
            ],
            id='high limit',
        ),
        pytest.param(
            2,
            [
                (['http://localhost:80/api/spaces'], 0, 2),
            ],
            id='low limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_spaces(
    get_current_datetime,
    dd_run_check,
    paginated_limit,
    mock_http_get,
    expected_skip_take_args,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        take = kwargs.get('params', {}).get('take')
        skip = kwargs.get('params', {}).get('skip')
        if 'http://localhost:80/api/spaces' == args[0]:
            skip_take_args += [(list(args), skip, take)]

    assert skip_take_args == expected_skip_take_args


@pytest.mark.parametrize(
    ('paginated_limit, expected_skip_take_args'),
    [
        pytest.param(
            30,
            [
                (['http://localhost:80/api/Spaces-1/projectgroups'], 0, 30),
            ],
            id='high limit',
        ),
        pytest.param(
            2,
            [
                (['http://localhost:80/api/Spaces-1/projectgroups'], 0, 2),
                (['http://localhost:80/api/Spaces-1/projectgroups'], 2, 2),
            ],
            id='low limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_project_groups(
    get_current_datetime,
    dd_run_check,
    paginated_limit,
    mock_http_get,
    expected_skip_take_args,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        take = kwargs.get('params', {}).get('take')
        skip = kwargs.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/projectgroups' == args[0]:
            skip_take_args += [(list(args), skip, take)]

    assert skip_take_args == expected_skip_take_args


@pytest.mark.parametrize(
    ('paginated_limit, expected_skip_take_args'),
    [
        pytest.param(
            30,
            [
                (['http://localhost:80/api/Spaces-1/projectgroups/ProjectGroups-1/projects'], 0, 30),
            ],
            id='high limit',
        ),
        pytest.param(
            2,
            [
                (['http://localhost:80/api/Spaces-1/projectgroups/ProjectGroups-1/projects'], 0, 2),
                (['http://localhost:80/api/Spaces-1/projectgroups/ProjectGroups-1/projects'], 2, 2),
            ],
            id='low limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_projects_projectgroups1(
    get_current_datetime,
    dd_run_check,
    paginated_limit,
    mock_http_get,
    expected_skip_take_args,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        take = kwargs.get('params', {}).get('take')
        skip = kwargs.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/projectgroups/ProjectGroups-1/projects' == args[0]:
            skip_take_args += [(list(args), skip, take)]

    assert skip_take_args == expected_skip_take_args


@pytest.mark.parametrize(
    ('paginated_limit, expected_skip_take_args'),
    [
        pytest.param(
            30,
            [
                (['http://localhost:80/api/Spaces-1/tasks'], 0, 30),
                (['http://localhost:80/api/Spaces-1/tasks'], 0, 30),
            ],
            id='high limit',
        ),
        pytest.param(
            2,
            [
                (['http://localhost:80/api/Spaces-1/tasks'], 0, 2),
                (['http://localhost:80/api/Spaces-1/tasks'], 0, 2),
            ],
            id='low limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_tasks(
    get_current_datetime,
    dd_run_check,
    paginated_limit,
    mock_http_get,
    expected_skip_take_args,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        take = kwargs.get('params', {}).get('take')
        skip = kwargs.get('params', {}).get('skip')
        project = kwargs.get('params', {}).get('project')
        if 'http://localhost:80/api/Spaces-1/tasks' == args[0] and project == 'Projects-1':
            skip_take_args += [(list(args), skip, take)]

    assert skip_take_args == expected_skip_take_args


@pytest.mark.parametrize(
    ('paginated_limit, expected_skip_take_args'),
    [
        pytest.param(
            30,
            [
                (['http://localhost:80/api/Spaces-1/environments'], 0, 30),
            ],
            id='high limit',
        ),
        pytest.param(
            2,
            [
                (['http://localhost:80/api/Spaces-1/environments'], 0, 2),
            ],
            id='low limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_environments(
    get_current_datetime,
    dd_run_check,
    paginated_limit,
    mock_http_get,
    expected_skip_take_args,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        take = kwargs.get('params', {}).get('take')
        skip = kwargs.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/environments' == args[0]:
            skip_take_args += [(list(args), skip, take)]

    assert skip_take_args == expected_skip_take_args


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_machines_metrics(
    get_current_datetime,
    dd_run_check,
    aggregator,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    aggregator.assert_metric(
        "octopus_deploy.machine.count",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "environment_name:dev",
            "machine_id:Machines-1",
            "machine_name:test-machine",
            "machine_slug:test-machine",
            "health_status:Healthy",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test-tag",
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.machine.is_healthy",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "environment_name:dev",
            "machine_id:Machines-1",
            "machine_name:test-machine",
            "machine_slug:test-machine",
            "health_status:Healthy",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test-tag",
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.machine.count",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "machine_id:Machines-2",
            "machine_name:test-machine1",
            "machine_slug:test-machine1",
            "health_status:Healthy with warnings",
            "operating_system:Ubuntu 24.04.1 LTS",
            "tag",
            "test",
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.machine.is_healthy",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "machine_id:Machines-2",
            "machine_name:test-machine1",
            "machine_slug:test-machine1",
            "health_status:Healthy with warnings",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test",
            "tag",
        ],
    )

    aggregator.assert_metric(
        "octopus_deploy.machine.count",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "environment_name:dev",
            "machine_id:Machines-3",
            "machine_name:test-machine3",
            "machine_slug:test-machine3",
            "health_status:Unhealthy",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test",
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.machine.is_healthy",
        0,
        tags=[
            'octopus_server:http://localhost:80',
            "environment_name:dev",
            "machine_id:Machines-3",
            "machine_name:test-machine3",
            "machine_slug:test-machine3",
            "health_status:Unhealthy",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test",
        ],
    )


@pytest.mark.parametrize(
    ('paginated_limit, expected_skip_take_args'),
    [
        pytest.param(
            30,
            [
                (['http://localhost:80/api/Spaces-1/machines'], 0, 30),
            ],
            id='high limit',
        ),
        pytest.param(
            2,
            [
                (['http://localhost:80/api/Spaces-1/machines'], 0, 2),
                (['http://localhost:80/api/Spaces-1/machines'], 2, 2),
            ],
            id='low limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_machines_pagination(
    get_current_datetime,
    dd_run_check,
    aggregator,
    expected_skip_take_args,
    mock_http_get,
    paginated_limit,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        take = kwargs.get('params', {}).get('take')
        skip = kwargs.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/machines' == args[0]:
            skip_take_args += [(list(args), skip, take)]

    assert skip_take_args == expected_skip_take_args

    aggregator.assert_metric(
        "octopus_deploy.machine.count",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "environment_name:dev",
            "machine_id:Machines-1",
            "machine_name:test-machine",
            "machine_slug:test-machine",
            "health_status:Healthy",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test-tag",
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.machine.is_healthy",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "environment_name:dev",
            "machine_id:Machines-1",
            "machine_name:test-machine",
            "machine_slug:test-machine",
            "health_status:Healthy",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test-tag",
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.machine.count",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "machine_id:Machines-2",
            "machine_name:test-machine1",
            "machine_slug:test-machine1",
            "health_status:Healthy with warnings",
            "operating_system:Ubuntu 24.04.1 LTS",
            "tag",
            "test",
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.machine.is_healthy",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "machine_id:Machines-2",
            "machine_name:test-machine1",
            "machine_slug:test-machine1",
            "health_status:Healthy with warnings",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test",
            "tag",
        ],
    )

    aggregator.assert_metric(
        "octopus_deploy.machine.count",
        1,
        tags=[
            'octopus_server:http://localhost:80',
            "environment_name:dev",
            "machine_id:Machines-3",
            "machine_name:test-machine3",
            "machine_slug:test-machine3",
            "health_status:Unhealthy",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test",
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.machine.is_healthy",
        0,
        tags=[
            "octopus_server:http://localhost:80",
            "environment_name:dev",
            "machine_id:Machines-3",
            "machine_name:test-machine3",
            "machine_slug:test-machine3",
            "health_status:Unhealthy",
            "operating_system:Ubuntu 24.04.1 LTS",
            "test",
        ],
    )


@pytest.mark.parametrize(
    ('disable_generic_tags, unified_service_tagging, expect_service_tags'),
    [
        pytest.param(
            True,
            True,
            False,
        ),
        pytest.param(
            True,
            False,
            False,
        ),
        pytest.param(
            False,
            True,
            True,
        ),
        pytest.param(
            False,
            False,
            False,
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_unified_service_tagging(
    get_current_datetime,
    dd_run_check,
    aggregator,
    disable_generic_tags,
    unified_service_tagging,
    expect_service_tags,
):
    instance = {'octopus_endpoint': 'http://localhost:80'}
    instance['disable_generic_tags'] = disable_generic_tags
    instance['unified_service_tagging'] = unified_service_tagging
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    if expect_service_tags:
        for metric in set(DEPLOY_METRICS) - set(COMPLETED_METRICS):
            aggregator.assert_metric_has_tag(metric, 'service:my-project', count=1)
            aggregator.assert_metric_has_tag(metric, 'env:staging', count=1)

        for metric in PROJECT_METRICS:
            aggregator.assert_metric_has_tag(metric, 'service:my-project', count=1)
            aggregator.assert_metric_has_tag(metric, 'env:staging', count=0)

        for metric in ENV_METRICS:
            aggregator.assert_metric_has_tag(metric, 'service:my-project', count=0)
            aggregator.assert_metric_has_tag(metric, 'env:staging', count=1)

    else:
        for metric in ALL_METRICS:
            aggregator.assert_metric_has_tag(metric, 'service:my-project', count=0)
            aggregator.assert_metric_has_tag(metric, 'env:staging', count=0)
