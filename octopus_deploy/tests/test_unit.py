# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.octopus_deploy import OctopusDeployCheck

from .constants import ALL_DEPLOYMENT_LOGS, ALL_EVENTS, ALL_METRICS, MOCKED_TIME1, MOCKED_TIME2, ONLY_TEST_LOGS


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

    aggregator.assert_metric('octopus_deploy.space.count', 1, tags=['space_id:Spaces-1', 'space_name:Default'])


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
        tags=['project_group_id:ProjectGroups-1', 'project_group_name:Default Project Group', 'space_name:Default'],
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=['project_group_id:ProjectGroups-2', 'project_group_name:test-group', 'space_name:Default'],
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=['project_group_id:ProjectGroups-3', 'project_group_name:hello', 'space_name:Default'],
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
            'project_id:Projects-3',
            'project_name:test',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        1,
        tags=['project_id:Projects-4', 'project_name:hi', 'project_group_name:test-group', 'space_name:Default'],
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
            'task_id:ServerTasks-118048',
            'task_name:Deploy',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        30,
        tags=[
            'task_id:ServerTasks-118048',
            'task_name:Deploy',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        150,
        tags=[
            'task_id:ServerTasks-118048',
            'task_name:Deploy',
            'task_state:Executing',
            'project_name:my-project',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        0,
        count=0,
        tags=[
            'task_id:ServerTasks-118048',
            'task_name:Deploy',
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
            'task_id:ServerTasks-118055',
            'task_name:Deploy',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        60,
        tags=[
            'task_id:ServerTasks-118055',
            'task_name:Deploy',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        0,
        count=0,
        tags=[
            'task_id:ServerTasks-118055',
            'task_name:Deploy',
            'task_state:Queued',
            'project_name:test',
            'space_name:Default',
            'server_node:None',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        0,
        count=0,
        tags=[
            'task_id:ServerTasks-118055',
            'task_name:Deploy',
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
            'project_name:test',
            'space_name:Default',
            'server_node:None',
            'task_id:ServerTasks-118055',
            'task_name:Deploy',
            'task_state:Queued',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'space_name:Default',
            'project_name:my-project',
            'server_node:OctopusServerNodes-50c3dfbarc82',
            'task_id:ServerTasks-118048',
            'task_name:Deploy',
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
            'task_id:ServerTasks-1847',
            'task_name:Deploy',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        110,
        tags=[
            'task_id:ServerTasks-1847',
            'task_name:Deploy',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        50,
        tags=[
            'task_id:ServerTasks-1847',
            'task_name:Deploy',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        5,
        tags=[
            'task_id:ServerTasks-1847',
            'task_name:Deploy',
            'task_state:Failed',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        1,
        tags=[
            'task_id:ServerTasks-1846',
            'task_name:Deploy',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        90,
        tags=[
            'task_id:ServerTasks-1846',
            'task_name:Deploy',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        54,
        tags=[
            'task_id:ServerTasks-1846',
            'task_name:Deploy',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        1,
        tags=[
            'task_id:ServerTasks-1846',
            'task_name:Deploy',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.count',
        tags=[
            'task_id:ServerTasks-1845',
            'task_name:Deploy',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.queued_time',
        18,
        tags=[
            'task_id:ServerTasks-1845',
            'task_name:Deploy',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.executing_time',
        41,
        tags=[
            'task_id:ServerTasks-1845',
            'task_name:Deploy',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
            'server_node:OctopusServerNodes-50c3dfbarc82',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.deployment.completed_time',
        14,
        tags=[
            'task_id:ServerTasks-1845',
            'task_name:Deploy',
            'task_state:Success',
            'project_name:test',
            'space_name:Default',
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

    aggregator.assert_metric('octopus_deploy.space.count', tags=['space_name:Default', 'space_name:First'], count=0)
    aggregator.assert_metric('octopus_deploy.space.count', tags=['space_id:Spaces-2', 'space_name:Second'])


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
        tags=['project_group_id:ProjectGroups-1', 'project_group_name:Default Project Group', 'space_name:Default'],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=['project_group_id:ProjectGroups-2', 'project_group_name:test-group', 'space_name:Default'],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=['project_group_id:ProjectGroups-3', 'project_group_name:hello', 'space_name:Default'],
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
        tags=['project_group_id:ProjectGroups-1', 'project_group_name:Default Project Group', 'space_name:Default'],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=['project_group_id:ProjectGroups-2', 'project_group_name:test-group', 'space_name:Default'],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=['project_group_id:ProjectGroups-3', 'project_group_name:hello', 'space_name:Default'],
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
            'project_id:Projects-1',
            'project_name:test-api',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        tags=[
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
            'project_name:test',
            'project_name:test',
            'project_group_name:Default Project Group',
            'space_name:Default',
        ],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project.count',
        tags=['project_id:Projects-4', 'project_name:hi', 'project_group_name:test-group', 'space_name:Default'],
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
        tags=['project_group_id:ProjectGroups-1', 'project_group_name:Default Project Group', 'space_name:Default'],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        tags=['project_group_id:ProjectGroups-2', 'project_group_name:test-group', 'space_name:Default'],
        count=0,
    )
    aggregator.assert_metric(
        'octopus_deploy.project_group.count',
        1,
        tags=['project_group_id:ProjectGroups-3', 'project_group_name:hello', 'space_name:Default'],
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
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.max_concurrent_tasks",
        5,
        count=1,
        tags=[
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.in_maintenance_mode",
        0,
        count=1,
        tags=[
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
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.max_concurrent_tasks",
        5,
        count=0,
        tags=[
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.in_maintenance_mode",
        5,
        count=0,
        tags=[
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
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.max_concurrent_tasks",
        5,
        count=1,
        tags=[
            'server_node_id:OctopusServerNodes-octopus-i8932-79236734bc234-09h234n',
            'server_node_name:octopus-i8932-79236734bc234-09h234n',
        ],
    )
    aggregator.assert_metric(
        "octopus_deploy.server_node.in_maintenance_mode",
        0,
        count=1,
        tags=[
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