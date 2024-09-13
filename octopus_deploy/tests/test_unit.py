# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import logging

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
            {'http_error': {'/api': MockResponse(status_code=500)}},
            'HTTPError: 500 Server Error: None for url: None',
            id='500',
        ),
        pytest.param(
            {'http_error': {'/api': MockResponse(status_code=404)}},
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


@pytest.mark.parametrize(
    'spaces_config, metric_count, project_group_metrics',
    [
        pytest.param(None, 1, PROJECT_GROUP_ALL_METRICS, id="default"),
        pytest.param({'include': ['Default']}, 1, PROJECT_GROUP_ALL_METRICS, id="include"),
        pytest.param({'include': ['Default'], 'limit': 1}, 1, PROJECT_GROUP_ALL_METRICS, id="within limit"),
        pytest.param({'include': ['Default'], 'limit': 0}, 0, PROJECT_GROUP_NO_METRICS, id="limit hit"),
        pytest.param({'include': ['Default'], 'exclude': ['Default']}, 0, PROJECT_GROUP_NO_METRICS, id="excluded"),
        pytest.param(
            {'include': ['Default'], 'exclude': ['test']}, 1, PROJECT_GROUP_ALL_METRICS, id="excluded invalid"
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_spaces_discovery(dd_run_check, aggregator, instance, spaces_config, metric_count, project_group_metrics):
    instance = copy.deepcopy(instance)
    instance['spaces'] = spaces_config
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    dd_run_check(check)
    tags = ["space_name:Default", "space_id:Spaces-1", "space_slug:default"]
    aggregator.assert_metric("octopus_deploy.space.count", count=metric_count, tags=tags)
    for metric in project_group_metrics:
        aggregator.assert_metric(metric["name"], count=metric["count"], tags=metric["tags"])
    aggregator.assert_metric("octopus_deploy.api.can_connect")
    aggregator.assert_metric("octopus_deploy.project.count", at_least=0)  # TODO: assert specific
    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'spaces_config, expected_metrics',
    [
        pytest.param(None, PROJECT_GROUP_ALL_METRICS, id="default"),
        pytest.param(
            {'include': [{'Default': {'project_groups': {'include': ['test-group']}}}]},
            PROJECT_GROUP_ONLY_TEST_GROUP_METRICS,
            id="include",
        ),
        pytest.param(
            {'include': [{'Default': {'project_groups': {'include': ['test-group'], 'limit': 1}}}]},
            PROJECT_GROUP_ONLY_TEST_GROUP_METRICS,
            id="within limit",
        ),
        pytest.param(
            {'include': [{'Default': {'project_groups': {'include': ['test-group'], 'limit': 0}}}]},
            PROJECT_GROUP_NO_METRICS,
            id="limit hit",
        ),
        pytest.param(
            {'include': [{'Default': {'project_groups': {'include': ['test-group'], 'exclude': ['test-group']}}}]},
            PROJECT_GROUP_NO_METRICS,
            id="excluded",
        ),
        pytest.param(
            {'include': [{'Default': {'project_groups': {'include': ['.*'], 'exclude': ['test-group']}}}]},
            PROJECT_GROUP_NO_TEST_GROUP_METRICS,
            id="one excluded",
        ),
        pytest.param(
            {'include': [{'Default': {'include': {'project_groups': ['test-group'], 'exclude': ['testing']}}}]},
            PROJECT_GROUP_ALL_METRICS,
            id="excluded invalud",
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_project_groups_discovery(dd_run_check, aggregator, instance, spaces_config, expected_metrics):
    instance = copy.deepcopy(instance)
    instance['spaces'] = spaces_config
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(metric["name"], count=metric["count"], tags=metric["tags"])


@pytest.mark.parametrize(
    'spaces_config, expected_metrics',
    [
        pytest.param(None, PROJECT_ALL_METRICS, id="default"),
        pytest.param(
            {
                'include': [
                    {'Default': {'project_groups': {'include': [{'test-group': {'projects': {'include': ['hi']}}}]}}}
                ]
            },
            PROJECT_ONLY_HI_METRICS,
            id="include",
        ),
        pytest.param(
            {
                'include': [
                    {
                        'Default': {
                            'project_groups': {'include': [{'.*': {'projects': {'include': ['.*'], 'limit': 1}}}]}
                        }
                    }
                ]
            },
            PROJECT_ONLY_HI_MY_PROJECT_METRICS,
            id="1 limit",
        ),
        pytest.param(
            {
                'include': [
                    {
                        'Default': {
                            'project_groups': {'include': [{'.*': {'projects': {'include': ['.*'], 'limit': 0}}}]}
                        }
                    }
                ]
            },
            PROJECT_NO_METRICS,
            id="limit hit",
        ),
        pytest.param(
            {
                'include': [
                    {
                        'Default': {
                            'project_groups': {
                                'exclude': ['Default.*'],
                                'include': [{'test-group': {'projects': {'include': ['.*']}}}],
                            }
                        }
                    }
                ]
            },
            PROJECT_ONLY_HI_METRICS,
            id="excluded default",
        ),
        pytest.param(
            {
                'include': [
                    {
                        'Default': {
                            'project_groups': {
                                'include': [{'.*': {'projects': {'include': ['.*'], 'exclude': ['.*']}}}]
                            }
                        }
                    }
                ]
            },
            PROJECT_NO_METRICS,
            id="all excluded",
        ),
        pytest.param(
            {
                'include': [
                    {
                        'Default': {
                            'include': {
                                'project_groups': {
                                    'include': [{'.*': {'projects': {'include': ['.*'], 'exclude': ['heyhey']}}}]
                                }
                            }
                        }
                    }
                ]
            },
            PROJECT_ALL_METRICS,
            id="excluded invalud",
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_projects_discovery(dd_run_check, aggregator, instance, spaces_config, expected_metrics, caplog):
    caplog.set_level(logging.DEBUG)
    instance = copy.deepcopy(instance)
    instance['spaces'] = spaces_config
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(metric["name"], count=metric["count"], tags=metric["tags"])
