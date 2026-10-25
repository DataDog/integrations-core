# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict
from urllib.parse import parse_qs, urlparse

import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.teamcity.common import filter_build_configs, filter_items, filter_projects, normalize_server_url

from .common import (
    CONFIG_ALL_BUILD_CONFIGS,
    CONFIG_ALL_BUILD_CONFIGS_WITH_LIMIT,
    CONFIG_ALL_PROJECTS,
    CONFIG_BAD_FORMAT,
    CONFIG_FILTERING_BUILD_CONFIGS,
    CONFIG_FILTERING_PROJECTS,
    CONFIG_MULTIPLE_PROJECTS_MAPPING,
    CONFIG_ONLY_EXCLUDE_ONE_BUILD_CONFIG,
    CONFIG_ONLY_EXCLUDE_ONE_PROJECT,
    CONFIG_ONLY_INCLUDE_ONE_BUILD_CONFIG,
    LEGACY_REST_INSTANCE,
    TEAMCITY_SERVER_VALUES,
    USE_OPENMETRICS,
)

pytestmark = [
    pytest.mark.skipif(USE_OPENMETRICS, reason='Not available in OpenMetrics version of check'),
    pytest.mark.unit,
]


def test_server_normalization():
    """
    Make sure server URLs are being normalized correctly
    """

    for server, expected_server in TEAMCITY_SERVER_VALUES.items():
        normalized_server = normalize_server_url(server)

        assert expected_server == normalized_server


@pytest.mark.parametrize(
    "to_filter, key, config, global_include, global_exclude, expected_result",
    [
        pytest.param(
            ['build_config1.prod', 'build_config1.tmp', 'build_config1.dev'],
            None,
            CONFIG_BAD_FORMAT,
            [],
            [],
            (OrderedDict({'build_config1.prod': None, 'build_config1.tmp': None, 'build_config1.dev': None}), False),
            id="Bad config",
        ),
        pytest.param(
            ['build_config1.prod', 'build_config1.tmp', 'build_config1.dev'],
            'build_configs',
            CONFIG_ALL_BUILD_CONFIGS,
            [],
            [],
            (
                OrderedDict([('build_config1.prod', None), ('build_config1.tmp', None), ('build_config1.dev', None)]),
                False,
            ),
            id="Include all build configs",
        ),
        pytest.param(
            ['build_config1.prod', 'build_config1.tmp', 'build_config1.dev'],
            'build_configs',
            CONFIG_ALL_BUILD_CONFIGS_WITH_LIMIT,
            [],
            [],
            (
                OrderedDict([('build_config1.prod', None), ('build_config1.tmp', None), ('build_config1.dev', None)]),
                False,
            ),
            id="Include all build configs with limit",
        ),
        pytest.param(
            ['build_config1.prod', 'build_config2.prod', 'build_config3.prod', 'build_config1.dev'],
            'build_configs',
            CONFIG_ONLY_INCLUDE_ONE_BUILD_CONFIG,
            [],
            [],
            (
                OrderedDict([('build_config1.prod', 'build_config1.*\\.prod')]),
                False,
            ),
            id="Include one build config",
        ),
        pytest.param(
            ['build_config1.prod', 'build_config2.prod', 'build_config3.prod', 'build_config1.dev'],
            'build_configs',
            CONFIG_ONLY_EXCLUDE_ONE_BUILD_CONFIG,
            [],
            [],
            (
                OrderedDict([('build_config1.prod', None), ('build_config2.prod', None), ('build_config3.prod', None)]),
                False,
            ),
            id="Exclude one build config",
        ),
        pytest.param(
            ['build_config1.prod'],
            'build_configs',
            CONFIG_FILTERING_BUILD_CONFIGS['projects']['include'][0]["project1.*\\.prod"],
            CONFIG_FILTERING_BUILD_CONFIGS['global_build_configs_include'],
            CONFIG_FILTERING_BUILD_CONFIGS['global_build_configs_exclude'],
            (OrderedDict([('build_config1.prod', 'build_config.*')]), False),
            id="Filter with all config options",
        ),
        pytest.param(
            ['build_config1.prod', 'build_config1.dev'],
            'build_configs',
            CONFIG_FILTERING_BUILD_CONFIGS['projects']['include'][0]["project1.*\\.prod"],
            CONFIG_FILTERING_BUILD_CONFIGS['global_build_configs_include'],
            CONFIG_FILTERING_BUILD_CONFIGS['global_build_configs_exclude'],
            (OrderedDict([('build_config1.prod', 'build_config.*'), ('build_config1.dev', 'build_config.*')]), False),
            id="Filter with all config options and override",
        ),
        pytest.param(
            ['build_config1.prod', 'build_config1.tmp', 'build_config1.dev'],
            'build_configs',
            CONFIG_FILTERING_BUILD_CONFIGS['projects']['include'][0]["project1.*\\.prod"],
            CONFIG_FILTERING_BUILD_CONFIGS['global_build_configs_include'],
            CONFIG_FILTERING_BUILD_CONFIGS['global_build_configs_exclude'],
            (
                OrderedDict(
                    [
                        ('build_config1.prod', 'build_config.*'),
                        ('build_config1.tmp', 'build_config.*'),
                        ('build_config1.dev', 'build_config.*'),
                    ]
                ),
                False,
            ),
            id="Filter with all config options and override",
        ),
        pytest.param(
            ['project1.prod', 'project2.prod', 'project1.dev'],
            'projects',
            CONFIG_ALL_PROJECTS,
            [],
            [],
            (OrderedDict([('project1.prod', None), ('project2.prod', None), ('project1.dev', None)]), False),
            id="Filter all projects",
        ),
        pytest.param(
            [
                'project1.prod',
                'project2.prod',
                'project1_fork.prod',
                'project3.prod',
                'project1.dev',
                'project10.prod',
                'project11_fork.prod',
                'project18.prod',
                'project12.prod',
            ],
            'projects',
            CONFIG_ALL_BUILD_CONFIGS,
            [],
            [],
            (
                OrderedDict(
                    [
                        ('project1.prod', {'project1.*\\.prod': {}}),
                        ('project1_fork.prod', {'project1.*\\.prod': {}}),
                        ('project10.prod', {'project1.*\\.prod': {}}),
                        ('project11_fork.prod', {'project1.*\\.prod': {}}),
                        ('project18.prod', {'project1.*\\.prod': {}}),
                    ]
                ),
                True,
            ),
            id="Filter all projects with limit",
        ),
        pytest.param(
            ['project1.prod', 'project2.prod', 'project1.dev', 'project1_draft.dev'],
            'projects',
            CONFIG_ONLY_EXCLUDE_ONE_PROJECT,
            [],
            [],
            (OrderedDict([('project1.prod', None), ('project2.prod', None)]), False),
            id="Filter projects with one exclude",
        ),
        pytest.param(
            ['project1.prod', 'project2.prod'],
            'projects',
            CONFIG_ALL_BUILD_CONFIGS_WITH_LIMIT,
            [],
            [],
            (OrderedDict([('project1.prod', {"project1.*\\.prod": {"limit": 3}})]), False),
            id="Filter projects with one include",
        ),
        pytest.param(
            ['project1.prod', 'project2.prod'],
            'projects',
            CONFIG_MULTIPLE_PROJECTS_MAPPING,
            [],
            [],
            (OrderedDict([('project1.prod', {'project1.*': {}}), ('project2.prod', {'project2.*': {}})]), False),
            id="Filter multiple projects",
        ),
        pytest.param(
            ['project1.prod', 'project2.prod', 'project2.dev', 'project1.tmp'],
            'projects',
            CONFIG_FILTERING_PROJECTS,
            [],
            [],
            (
                OrderedDict(
                    [
                        ('project1.prod', {'project1.*': {}}),
                        ('project2.prod', {'project2.*': {}}),
                        ('project2.dev', {'project2.*': {}}),
                    ]
                ),
                False,
            ),
            id="Filter multiple projects with overlap and exclude override",
        ),
    ],
)
def test_filter_items(to_filter, key, config, global_include, global_exclude, expected_result):
    filtered = filter_items(to_filter, key, 5, global_include, global_exclude, config)
    assert filtered == expected_result


@pytest.mark.parametrize(
    "projects_config, projects_to_filter, expected_result",
    [
        pytest.param(
            {},
            ['Project1', 'Project2', 'ProjectB'],
            (OrderedDict([('Project1', None), ('Project2', None), ('ProjectB', None)]), False),
            id="Filter projects, default include all",
        ),
        pytest.param(
            {'include': [{'Project1': {}}, {'ProjectB': {}}, {'ProjectX': {}}]},
            ['Project1', 'Project2', 'ProjectB'],
            (OrderedDict([('Project1', {'Project1': {}}), ('ProjectB', {'ProjectB': {}})]), False),
            id="Filter projects, only include",
        ),
        pytest.param(
            {'exclude': [{'ProjectA': {}}, {'ProjectB': {}}]},
            ['Project1', 'Project2', 'ProjectB'],
            (OrderedDict([('Project1', None), ('Project2', None)]), False),
            id="Filter projects, only exclude",
        ),
        pytest.param(
            {'include': [{'Project1': {}}, {'Project2': {}}], 'exclude': [{'ProjectA': {}}, {'ProjectB': {}}]},
            ['Project1', 'Project2', 'ProjectA', 'ProjectB', 'ProjectC'],
            (OrderedDict([('Project1', {'Project1': {}}), ('Project2', {'Project2': {}})]), False),
            id="Filter projects, include and exclude",
        ),
        pytest.param(
            {'include': [{'Project(.*)_Prod.*': {}}], 'exclude': [{'Project(.*)_Dev': {}}, {'Project(.*)_Test': {}}]},
            ['ProjectA_Test.1', 'ProjectA_Prod.2', 'ProjectA_Dev.1', 'ProjectB_Prod.3', 'ProjectC'],
            (
                OrderedDict(
                    [('ProjectA_Prod.2', {'Project(.*)_Prod.*': {}}), ('ProjectB_Prod.3', {'Project(.*)_Prod.*': {}})]
                ),
                False,
            ),
            id="Filter projects, include and exclude regex",
        ),
    ],
)
def test_filter_projects(projects_config, projects_to_filter, expected_result, rest_instance, teamcity_rest_check):
    rest_instance['projects'] = projects_config
    check = teamcity_rest_check(rest_instance)
    filtered = filter_projects(check, projects_to_filter)

    assert filtered == expected_result


@pytest.mark.parametrize(
    "build_configs_to_filter, filter_config, expected_result",
    [
        pytest.param(
            ['BuildStep1', 'BuildStep2', 'BuildStep3', 'DeploymentA'],
            {},
            (
                OrderedDict(
                    [
                        ('BuildStep1', None),
                        ('BuildStep2', None),
                        ('BuildStep3', None),
                        ('DeploymentA', None),
                    ]
                ),
                False,
            ),
            id="Filter build configs, default include all",
        ),
        pytest.param(
            ['BuildStep1', 'BuildStep2', 'BuildStep3', 'DeploymentA'],
            {'include': ['BuildStep.*']},
            (
                OrderedDict(
                    [
                        ('BuildStep1', 'BuildStep.*'),
                        ('BuildStep2', 'BuildStep.*'),
                        ('BuildStep3', 'BuildStep.*'),
                    ]
                ),
                False,
            ),
            id="Filter build configs, only include",
        ),
        pytest.param(
            ['BuildStep1', 'BuildStep2', 'Deployment.prod.1', 'Deployment.dev.1', 'Deployment.dev.5'],
            {'exclude': ['Deployment.dev.*']},
            (
                OrderedDict(
                    [
                        ('BuildStep1', None),
                        ('BuildStep2', None),
                        ('Deployment.prod.1', None),
                    ]
                ),
                False,
            ),
            id="Filter build configs, only exclude",
        ),
        pytest.param(
            ['BuildStep1', 'BuildStep2', 'Deployment.dev.1', 'Deployment.prod.1', 'Deployment.prod.2'],
            {'include': ['BuildStep.*', 'Deployment.prod.*'], 'exclude': ['Deployment.dev.*']},
            (
                OrderedDict(
                    [
                        ('BuildStep1', 'BuildStep.*'),
                        ('BuildStep2', 'BuildStep.*'),
                        ('Deployment.prod.1', 'Deployment.prod.*'),
                        ('Deployment.prod.2', 'Deployment.prod.*'),
                    ]
                ),
                False,
            ),
            id="Filter build configs, include and exclude regex",
        ),
    ],
)
def test_filter_build_configs(
    build_configs_to_filter, filter_config, expected_result, rest_instance, teamcity_rest_check
):
    check = teamcity_rest_check(rest_instance)
    filtered = filter_build_configs(check, build_configs_to_filter, 'ProjectID', {'ProjectID': filter_config})

    assert filtered == expected_result


def test_collects_build_config_without_default_branch_builds(dd_run_check, aggregator, mocker, teamcity_rest_check):
    """
    TeamCity's default build filter hides builds outside the default branch, as well as personal, canceled,
    and failed-to-start builds. A build configuration whose builds all fall in that set, such as one that
    only builds pull request branches, must still be collected.
    """
    build_config = LEGACY_REST_INSTANCE['build_configuration']
    builds = []

    def add_pull_request_build(build_id):
        builds.insert(
            0,
            {
                'id': build_id,
                'buildTypeId': build_config,
                'number': str(build_id),
                'status': 'SUCCESS',
                'state': 'finished',
                'branchName': 'pull/{}'.format(build_id),
                'webUrl': 'http://localhost:8111/viewLog.html?buildId={}'.format(build_id),
            },
        )

    def teamcity_api(url, **kwargs):
        parsed_url = urlparse(url)
        if parsed_url.path.endswith('/app/rest/builds/'):
            locator = parse_qs(parsed_url.query)['locator'][0]
            # Without `defaultFilter:false`, TeamCity only returns default branch builds.
            matching = builds if 'defaultFilter:false' in locator else []
            if 'sinceBuild:id:' in locator:
                since_build = int(locator.split('sinceBuild:id:')[1].split(',')[0])
                matching = [build for build in matching if build['id'] > since_build]
            if 'count:1' in locator:
                matching = matching[:1]
            return MockResponse(json_data={'count': len(matching), 'build': matching})
        if parsed_url.path.endswith('/app/rest/buildTypes/id:{}'.format(build_config)):
            return MockResponse(json_data={'id': build_config, 'projectId': 'SampleProject'})
        return MockResponse(json_data={'count': 0})

    mocker.patch('requests.Session.get', side_effect=teamcity_api)
    instance = dict(
        LEGACY_REST_INSTANCE, build_config_metrics=False, tests_health_check=False, build_problem_health_check=False
    )
    check = teamcity_rest_check(instance)

    add_pull_request_build(100)
    dd_run_check(check)
    add_pull_request_build(101)
    dd_run_check(check)

    assert ['build_id:101' in event['tags'] for event in aggregator.events] == [True]
