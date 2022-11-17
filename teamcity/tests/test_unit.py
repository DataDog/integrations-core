# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict

import pytest
from six import PY2, iteritems

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
    TEAMCITY_SERVER_VALUES,
    USE_OPENMETRICS,
)

pytestmark = [
    pytest.mark.skipif(USE_OPENMETRICS, reason='Not available in OpenMetrics version of check'),
    pytest.mark.skipif(PY2, reason='Not available in Python 2'),
    pytest.mark.unit,
]


def test_server_normalization():
    """
    Make sure server URLs are being normalized correctly
    """

    for server, expected_server in iteritems(TEAMCITY_SERVER_VALUES):
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
            {'include': [{'Project1': {}}, {'ProjectB': {}}, {'ProjectX': {}}]},
            ['_Root', 'Project1', 'Project2', 'ProjectB'],
            (OrderedDict([('Project1', {'Project1': {}}), ('ProjectB', {'ProjectB': {}})]), False),
            id="Filter projects, only include",
        )
    ],
)
def test_filter_projects(projects_config, projects_to_filter, expected_result, rest_instance, teamcity_rest_check):
    rest_instance['projects'] = projects_config
    check = teamcity_rest_check(rest_instance)
    filtered = filter_projects(check, projects_to_filter)

    assert filtered == expected_result


@pytest.mark.parametrize(
    "build_configs_to_filter, project_id_pattern, filter_config, expected_result",
    [
        pytest.param(
            [
                'ProjectA_BuildStep1',
                'ProjectA_BuildStep2',
                'ProjectA_BuildStep3',
                'ProjectA_BuildStep4',
                'ProjectA_Deployment'
            ],
            'SampleProject',
            {'SampleProject': {}},
            (
                OrderedDict(
                    [
                        ('ProjectA_BuildStep1', None),
                        ('ProjectA_BuildStep2', None),
                        ('ProjectA_BuildStep3', None),
                        ('ProjectA_BuildStep4', None),
                        ('ProjectA_Deployment', None),
                    ]
                ),
                False,
            ),
            id="Filter build configs, only include",
        )
    ],
)
def test_filter_build_configs(
    build_configs_to_filter, project_id_pattern, filter_config, expected_result, rest_instance, teamcity_rest_check
):
    check = teamcity_rest_check(rest_instance)
    filtered = filter_build_configs(check, build_configs_to_filter, project_id_pattern, filter_config)

    assert filtered == expected_result
