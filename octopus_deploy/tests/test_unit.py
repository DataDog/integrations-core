# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import logging

import mock
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.octopus_deploy import OctopusDeployCheck

from .constants import (
    ALL_METRICS,
    PROJECT_ALL_METRICS,
    PROJECT_GROUP_ALL_METRICS,
    PROJECT_GROUP_NO_METRICS,
    PROJECT_GROUP_NO_TEST_GROUP_METRICS,
    PROJECT_GROUP_ONLY_TEST_GROUP_METRICS,
    PROJECT_NO_METRICS,
    PROJECT_ONLY_HI_METRICS,
    PROJECT_ONLY_HI_MY_PROJECT_METRICS,
)


@pytest.mark.usefixtures('mock_http_get')
def test_check(dd_run_check, aggregator, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.api.can_connect', 1)
    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    ('mock_http_get, message'),
    [
        pytest.param(
            {'http_error': {'/api/spaces': MockResponse(status_code=500)}},
            'HTTPError: 500 Server Error: None for url: None',
            id='500',
        ),
        pytest.param(
            {'http_error': {'/api/spaces': MockResponse(status_code=404)}},
            'HTTPError: 404 Client Error: None for url: None',
            id='404',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance, message):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    with pytest.raises(Exception, match=message):
        dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.api.can_connect', 0)
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('mock_http_get')
def test_space_invalid(dd_run_check, aggregator, instance):
    invalid_space_instance = copy.deepcopy(instance)
    invalid_space_instance['space'] = 'test'
    check = OctopusDeployCheck('octopus_deploy', {}, [invalid_space_instance])
    with pytest.raises(Exception, match=r'Space ID not found for provided space name test, does it exist'):
        dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.api.can_connect', 1)
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('mock_http_get')
def test_space_cached(dd_run_check, aggregator, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    check._get_space_id = mock.MagicMock()
    check.space_id = "Spaces-1"
    dd_run_check(check)

    assert check._get_space_id.call_count == 0
    aggregator.assert_metric('octopus_deploy.api.can_connect', 1)


@pytest.mark.parametrize(
    'project_groups_config, expected_metrics',
    [
        pytest.param(None, PROJECT_GROUP_ALL_METRICS, id="default"),
        pytest.param(
            {'include': []},
            PROJECT_GROUP_ALL_METRICS,
            id="empty include",
        ),
        pytest.param(
            {'include': ['test-group']},
            PROJECT_GROUP_ONLY_TEST_GROUP_METRICS,
            id="include",
        ),
        pytest.param(
            {'include': ['test-group'], 'limit': 1},
            PROJECT_GROUP_ONLY_TEST_GROUP_METRICS,
            id="within limit",
        ),
        pytest.param(
            {'include': ['test-group'], 'limit': 0},
            PROJECT_GROUP_NO_METRICS,
            id="limit hit",
        ),
        pytest.param(
            {'include': ['test-group'], 'exclude': ['test-group']},
            PROJECT_GROUP_NO_METRICS,
            id="excluded",
        ),
        pytest.param(
            {'include': ['.*'], 'exclude': ['test-group']},
            PROJECT_GROUP_NO_TEST_GROUP_METRICS,
            id="one excluded",
        ),
        pytest.param(
            {'include': ['.*'], 'exclude': ['testing']},
            PROJECT_GROUP_ALL_METRICS,
            id="excluded invalid",
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_project_groups_discovery(dd_run_check, aggregator, instance, project_groups_config, expected_metrics):
    instance = copy.deepcopy(instance)
    instance['project_groups'] = project_groups_config
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(metric["name"], count=metric["count"], tags=metric["tags"])


@pytest.mark.usefixtures('mock_http_get')
def test_project_groups_discovery_error(dd_run_check, instance):
    instance = copy.deepcopy(instance)
    instance['project_groups'] = {'include': None}
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    with pytest.raises(Exception, match=r'Setting `include` must be an array'):
        dd_run_check(check)


@pytest.mark.parametrize(
    'project_groups_config, expected_metrics',
    [
        pytest.param(None, PROJECT_ALL_METRICS, id="default"),
        pytest.param(
            {'include': [{'test-group': {'projects': {'include': ['hi']}}}]},
            PROJECT_ONLY_HI_METRICS,
            id="include",
        ),
        pytest.param(
            {'include': [{'.*': {'projects': {'include': ['.*'], 'limit': 1}}}]},
            PROJECT_ONLY_HI_MY_PROJECT_METRICS,
            id="1 limit",
        ),
        pytest.param(
            {'include': [{'.*': {'projects': {'include': ['.*'], 'limit': 0}}}]},
            PROJECT_NO_METRICS,
            id="limit hit",
        ),
        pytest.param(
            {
                'exclude': ['Default.*'],
                'include': [{'test-group': {'projects': {'include': ['.*']}}}],
            },
            PROJECT_ONLY_HI_METRICS,
            id="excluded default",
        ),
        pytest.param(
            {'include': [{'.*': {'projects': {'include': ['.*'], 'exclude': ['.*']}}}]},
            PROJECT_NO_METRICS,
            id="all excluded",
        ),
        pytest.param(
            {'include': [{'.*': {'projects': {'include': ['.*'], 'exclude': ['heyhey']}}}]},
            PROJECT_ALL_METRICS,
            id="excluded invalud",
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_projects_discovery(dd_run_check, aggregator, instance, project_groups_config, expected_metrics, caplog):
    caplog.set_level(logging.DEBUG)
    instance = copy.deepcopy(instance)
    instance['project_groups'] = project_groups_config
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(metric["name"], count=metric["count"], tags=metric["tags"])
