# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import logging
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
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
                    '/api/spaces': FakeHTTPResponse(status_code=500),
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
def test_can_connect(get_current_datetime, dd_run_check, aggregator, expected_exception, can_connect, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    with expected_exception:
        dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.api.can_connect', can_connect)


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_no_filtering(get_current_datetime, dd_run_check):
    instance = {'octopus_endpoint': 'http://localhost:80'}

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    with pytest.raises(
        Exception, match="A configuration for projects, project_groups, or spaces is required for this integratio"
    ):
        dd_run_check(check)


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_all_metrics_covered(get_current_datetime, dd_run_check, aggregator, instance):
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
def test_empty_spaces(get_current_datetime, dd_run_check, aggregator, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.space.count', count=0)


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_one_space(get_current_datetime, dd_run_check, aggregator, instance):
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
def test_project_groups(get_current_datetime, dd_run_check, aggregator, instance):
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
def test_projects(get_current_datetime, dd_run_check, aggregator, instance):
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
def test_queued_or_running_tasks(get_current_datetime, dd_run_check, aggregator, instance):
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
def test_completed_tasks(get_current_datetime, dd_run_check, aggregator, instance):
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
                    '/api/Spaces-1/tasks': FakeHTTPResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/tasks: 500 Server Error',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_tasks_endpoint_unavailable(get_current_datetime, dd_run_check, expected_log, caplog, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.WARNING)
    dd_run_check(check)
    assert expected_log in caplog.text


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_server_node_metrics(get_current_datetime, dd_run_check, aggregator, instance):
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
                    '/api/octopusservernodes': FakeHTTPResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/octopusservernodes: 500 Server Error',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_server_node_endpoint_failed(get_current_datetime, dd_run_check, aggregator, expected_log, caplog, instance):
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
    instance = copy.deepcopy(instance)
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
def test_events(get_current_datetime, dd_run_check, aggregator, expected_events, events_enabled, instance):
    instance = copy.deepcopy(instance)
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
def test_environment_metrics(get_current_datetime, dd_run_check, aggregator, instance):
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
def test_environments_discovery_one_include(get_current_datetime, dd_run_check, aggregator, instance):
    instance = copy.deepcopy(instance)
    instance['environments'] = {'include': ['dev']}

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
def test_environments_discovery_exclude_dev(get_current_datetime, dd_run_check, aggregator, instance):
    instance = copy.deepcopy(instance)
    instance['environments'] = {'exclude': ['dev'], 'include': ['.*']}

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
def test_environments_discovery_include_invalid(get_current_datetime, dd_run_check, aggregator, instance):
    instance = copy.deepcopy(instance)
    instance['environments'] = {'include': ['test']}

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
                    '/api/Spaces-1/environments': FakeHTTPResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/environments: 500 Server Error',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_environments_metrics_http_failure(
    get_current_datetime, dd_run_check, aggregator, expected_log, caplog, instance
):
    instance = copy.deepcopy(instance)
    instance['environments'] = {'include': ['test']}

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
                    '/api/Spaces-1/releases/Releases-3': FakeHTTPResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/releases/Releases-3: 500 Server Error',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_deployment_metrics_releases_http_failure(
    get_current_datetime, dd_run_check, aggregator, expected_log, caplog, instance
):
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
                    '/api/Spaces-1/deployments': FakeHTTPResponse(status_code=500),
                    '/api/Spaces-1/deployments/Deployments-18': FakeHTTPResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/deployments/Deployments-18: 500 Server Error',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_deployment_metrics_deployments_http_failure(
    get_current_datetime, dd_run_check, aggregator, expected_log, caplog, instance
):
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
                    '/api/Spaces-1/environments': FakeHTTPResponse(status_code=500),
                }
            },
            'Failed to access endpoint: api/Spaces-1/environments: 500 Server Error',
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_deployment_metrics_environments_http_failure(
    get_current_datetime, dd_run_check, aggregator, expected_log, caplog, instance
):
    instance = copy.deepcopy(instance)
    instance['environments'] = {'include': ['test']}

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
def test_deployments_caching(get_current_datetime, dd_run_check, mock_http_get, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)
    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)

    args_list = []
    bulk_deployment_ids = []
    for request in mock_http_get.requests:
        args_list += [request.url]
        if request.url == 'http://localhost:80/api/Spaces-1/deployments':
            bulk_deployment_ids.append(request.options.get('params', {}).get('ids'))

    # Deployments are looked up in bulk, only on the run that first sees them.
    assert bulk_deployment_ids == [['Deployments-18', 'Deployments-19'], ['Deployments-16', 'Deployments-17']]
    # Individual deployment lookups are the fallback for a cache miss, and must not run when the bulk lookup succeeded.
    for deployment_id in ['Deployments-16', 'Deployments-17', 'Deployments-18', 'Deployments-19']:
        assert args_list.count(f'http://localhost:80/api/Spaces-1/deployments/{deployment_id}') == 0

    # Each release is fetched by id exactly once across all runs, never through the releases collection.
    for release_id in ['Releases-1', 'Releases-2', 'Releases-3']:
        assert args_list.count(f'http://localhost:80/api/Spaces-1/releases/{release_id}') == 1
    assert args_list.count('http://localhost:80/api/Spaces-1/releases') == 0

    assert args_list.count('http://localhost:80/api/Spaces-1/environments') == 5


@pytest.mark.parametrize(
    ('paginated_limit'),
    [pytest.param(30, id='high limit'), pytest.param(2, id='low limit')],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_octopusservernodes(
    get_current_datetime, dd_run_check, aggregator, paginated_limit, mock_http_get, instance
):
    instance = copy.deepcopy(instance)
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    args_list = []
    for request in mock_http_get.requests:
        args_list += [request.url]
        take = request.options.get('params', {}).get('take')
        skip = request.options.get('params', {}).get('skip')
        args_list += [(request.url, take, skip)]

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
    instance,
):
    instance = copy.deepcopy(instance)
    instance['paginated_limit'] = paginated_limit
    instance['collect_events'] = True

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    get_current_datetime.return_value = MOCKED_TIME2
    dd_run_check(check)

    skip_take_args = []
    for request in mock_http_get.requests:
        take = request.options.get('params', {}).get('take')
        skip = request.options.get('params', {}).get('skip')
        if 'events' in request.url:
            skip_take_args += [([request.url], skip, take)]

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
    get_current_datetime, dd_run_check, paginated_limit, mock_http_get, expected_skip_take_args, instance
):
    instance = copy.deepcopy(instance)
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for request in mock_http_get.requests:
        take = request.options.get('params', {}).get('take')
        skip = request.options.get('params', {}).get('skip')
        if 'http://localhost:80/api/spaces' == request.url:
            skip_take_args += [([request.url], skip, take)]

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
    get_current_datetime, dd_run_check, paginated_limit, mock_http_get, expected_skip_take_args, instance
):
    instance = copy.deepcopy(instance)
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for request in mock_http_get.requests:
        take = request.options.get('params', {}).get('take')
        skip = request.options.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/projectgroups' == request.url:
            skip_take_args += [([request.url], skip, take)]

    assert skip_take_args == expected_skip_take_args


@pytest.mark.parametrize(
    ('paginated_limit, expected_skip_take_args'),
    [
        pytest.param(
            30,
            [
                (['http://localhost:80/api/Spaces-1/projects'], 0, 30),
            ],
            id='high limit',
        ),
        pytest.param(
            2,
            [
                (['http://localhost:80/api/Spaces-1/projects'], 0, 2),
                (['http://localhost:80/api/Spaces-1/projects'], 2, 2),
            ],
            id='low limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_paginated_limit_projects(
    get_current_datetime, dd_run_check, paginated_limit, mock_http_get, expected_skip_take_args, instance
):
    instance = copy.deepcopy(instance)
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for request in mock_http_get.requests:
        take = request.options.get('params', {}).get('take')
        skip = request.options.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/projects' == request.url:
            skip_take_args += [([request.url], skip, take)]

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
    get_current_datetime, dd_run_check, paginated_limit, mock_http_get, expected_skip_take_args, instance
):
    instance = copy.deepcopy(instance)
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for request in mock_http_get.requests:
        take = request.options.get('params', {}).get('take')
        skip = request.options.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/tasks' == request.url:
            skip_take_args += [([request.url], skip, take)]

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
    get_current_datetime, dd_run_check, paginated_limit, mock_http_get, expected_skip_take_args, instance
):
    instance = copy.deepcopy(instance)
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for request in mock_http_get.requests:
        take = request.options.get('params', {}).get('take')
        skip = request.options.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/environments' == request.url:
            skip_take_args += [([request.url], skip, take)]

    assert skip_take_args == expected_skip_take_args


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_machines_metrics(get_current_datetime, dd_run_check, aggregator, instance):
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
            "role_name:test-tag",
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
            "role_name:test-tag",
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
            "role_name:tag",
            "role_name:test",
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
            "role_name:tag",
            "role_name:test",
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
            "role_name:test",
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
            "role_name:test",
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
    get_current_datetime, dd_run_check, aggregator, expected_skip_take_args, mock_http_get, paginated_limit, instance
):
    instance = copy.deepcopy(instance)
    instance['paginated_limit'] = paginated_limit

    check = OctopusDeployCheck('octopus_deploy', {}, [instance])

    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    skip_take_args = []
    for request in mock_http_get.requests:
        take = request.options.get('params', {}).get('take')
        skip = request.options.get('params', {}).get('skip')
        if 'http://localhost:80/api/Spaces-1/machines' == request.url:
            skip_take_args += [([request.url], skip, take)]

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
            "role_name:test-tag",
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
            "role_name:test-tag",
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
            "role_name:tag",
            "role_name:test",
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
            "role_name:tag",
            "role_name:test",
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
            "role_name:test",
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
            "role_name:test",
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
    instance,
):
    instance = copy.deepcopy(instance)
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


@pytest.mark.parametrize(
    ('mock_http_get', 'projects_config', 'expected_exception', 'can_connect'),
    [
        pytest.param(
            {'http_error': {'/api/Spaces-1/projects': FakeHTTPResponse(status_code=500)}},
            {'include': ['.*']},
            pytest.raises(Exception, match=r'Could not connect to octopus API.*'),
            0,
            id='projects discovery reports the failure',
        ),
        pytest.param(
            {'http_error': {'/api/Spaces-1/projects': FakeHTTPResponse(status_code=500)}},
            None,
            does_not_raise(),
            1,
            id='default listing only warns',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_projects_listing_failure(
    get_current_datetime, dd_run_check, aggregator, instance, projects_config, expected_exception, can_connect
):
    instance = copy.deepcopy(instance)
    if projects_config:
        instance['projects'] = projects_config
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1

    with expected_exception:
        dd_run_check(check)

    # With a `projects` filter configured, a failed listing must not look like a healthy API with no projects.
    aggregator.assert_metric('octopus_deploy.api.can_connect', can_connect, count=1)
    aggregator.assert_metric('octopus_deploy.project.count', count=0)


@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_collection_does_not_scale_with_project_count(get_current_datetime, dd_run_check, mock_http_get, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    urls = [request.url for request in mock_http_get.requests]

    # The space holds four projects across three project groups, but each collection is listed once for the space.
    assert urls.count('http://localhost:80/api/Spaces-1/projects') == 1
    assert urls.count('http://localhost:80/api/Spaces-1/projectgroups') == 1
    # One call for queued/executing tasks and one for the tasks completed during the interval.
    assert urls.count('http://localhost:80/api/Spaces-1/tasks') == 2
    # Deployments are resolved with one bulk lookup, not one per task.
    assert urls.count('http://localhost:80/api/Spaces-1/deployments') == 1


# Some Octopus versions ignore the `ids` filter on collection endpoints and return the whole, paginated history.
UNFILTERED_DEPLOYMENTS = {
    'Items': [
        {'Id': f'Deployments-{n}', 'ReleaseId': f'Releases-{n}', 'EnvironmentId': 'Environments-1'}
        for n in range(9000, 9300)
    ],
    'TotalResults': 4800,
    'ItemsPerPage': 300,
    'NumberOfPages': 16,
}


@pytest.mark.parametrize(
    'mock_http_get', [pytest.param({'mock_data': {'/api/Spaces-1/deployments': UNFILTERED_DEPLOYMENTS}})], indirect=True
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.octopus_deploy.check.get_current_datetime")
def test_bulk_lookup_bounded_when_ids_filter_is_ignored(
    get_current_datetime, dd_run_check, aggregator, mock_http_get, instance
):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    get_current_datetime.return_value = MOCKED_TIME1
    dd_run_check(check)

    urls = [request.url for request in mock_http_get.requests]

    # A single request rather than a walk through all 16 pages of deployment history.
    assert urls.count('http://localhost:80/api/Spaces-1/deployments') == 1
    # Nothing is looked up for deployments the check never asked for.
    assert not [url for url in urls if '/releases/Releases-9' in url]
    # The requested deployments fall back to individual lookups and keep their real tags.
    assert urls.count('http://localhost:80/api/Spaces-1/deployments/Deployments-18') == 1
    assert urls.count('http://localhost:80/api/Spaces-1/deployments/Deployments-19') == 1
    aggregator.assert_metric_has_tag('octopus_deploy.deployment.count', 'release_version:0.0.1', count=1)
    aggregator.assert_metric_has_tag('octopus_deploy.deployment.count', 'release_version:0.0.2', count=1)


@pytest.mark.parametrize(
    ('retry_after', 'expected_wait'),
    [
        pytest.param({'Retry-After': '7'}, 7.0, id='retry-after seconds'),
        pytest.param({'Retry-After': '900'}, 10.0, id='retry-after above the cap'),
        pytest.param({'Retry-After': 'Wed, 21 Oct 2015 07:28:00 GMT'}, 1.0, id='retry-after http date'),
        pytest.param({}, 1.0, id='no retry-after header'),
    ],
)
def test_throttled_request_waits_then_succeeds(instance, fake_http, fake_http_response, retry_after, expected_wait):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    check.load_configuration_models()
    spaces_url = f"{instance['octopus_endpoint']}/api/spaces"
    fake_http_response(spaces_url, status_code=429, headers=retry_after)
    fake_http_response(spaces_url, json_data={'Items': ['a space']})

    with mock.patch('datadog_checks.octopus_deploy.check.time.sleep') as sleep:
        assert check._process_endpoint('api/spaces') == {'Items': ['a space']}

    fake_http.assert_all_responses_consumed()
    sleep.assert_called_once_with(expected_wait)


def test_throttled_request_gives_up_after_bounded_retries(instance, fake_http, fake_http_response, caplog):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    check.load_configuration_models()
    caplog.set_level(logging.WARNING)
    # The initial attempt and three retries. A further retry would find no registered response and fail the test.
    for _ in range(4):
        fake_http_response(f"{instance['octopus_endpoint']}/api/spaces", status_code=429, headers={'Retry-After': '1'})

    with mock.patch('datadog_checks.octopus_deploy.check.time.sleep') as sleep:
        assert check._process_endpoint('api/spaces') == {}

    # Three retries after the initial attempt, then the throttled response is surfaced instead of retrying forever.
    fake_http.assert_all_responses_consumed()
    assert sleep.call_count == 3
    assert 'Failed to access endpoint: api/spaces' in caplog.text
