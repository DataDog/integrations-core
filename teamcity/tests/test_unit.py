# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from six import iteritems

from datadog_checks.teamcity import TeamCityCheck
from datadog_checks.teamcity.common import construct_build_configs_filter, should_include_build_config

from .common import CHECK_NAME

# A path regularly used in the TeamCity Check
COMMON_PATH = "guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS"

# These values are acceptable URLs
TEAMCITY_SERVER_VALUES = {
    # Regular URLs
    "localhost:8111/httpAuth": "http://localhost:8111/httpAuth",
    "localhost:8111/{}".format(COMMON_PATH): "http://localhost:8111/{}".format(COMMON_PATH),
    "http.com:8111/{}".format(COMMON_PATH): "http://http.com:8111/{}".format(COMMON_PATH),
    "http://localhost:8111/some_extra_url_with_http://": "http://localhost:8111/some_extra_url_with_http://",
    "https://localhost:8111/correct_url_https://": "https://localhost:8111/correct_url_https://",
    "https://localhost:8111/{}".format(COMMON_PATH): "https://localhost:8111/{}".format(COMMON_PATH),
    "http://http.com:8111/{}".format(COMMON_PATH): "http://http.com:8111/{}".format(COMMON_PATH),
    # <user>:<password>@teamcity.company.com
    "user:password@localhost:8111/http://_and_https://": "http://user:password@localhost:8111/http://_and_https://",
    "user:password@localhost:8111/{}".format(COMMON_PATH): "http://user:password@localhost:8111/{}".format(COMMON_PATH),
    "http://user:password@localhost:8111/{}".format(COMMON_PATH): "http://user:password@localhost:8111/{}".format(
        COMMON_PATH
    ),
    "https://user:password@localhost:8111/{}".format(COMMON_PATH): "https://user:password@localhost:8111/{}".format(
        COMMON_PATH
    ),
}


def test_server_normalization():
    """
    Make sure server URLs are being normalized correctly
    """

    teamcity = TeamCityCheck(CHECK_NAME, {}, [{'server': 'localhost:8111', 'use_openmetrics': False}])

    for server, expected_server in iteritems(TEAMCITY_SERVER_VALUES):
        normalized_server = teamcity._normalize_server_url(server)

        assert expected_server == normalized_server


@pytest.mark.parametrize(
    'projects_config, expected_exclude, expected_include, sample_build_configs, should_include',
    [
        pytest.param({'project_a': {}}, set(), set(), ['A_build_foo', ['A_build_bar']], [True, True], id="No filters"),
        pytest.param(
            {'project_A': {'include': ['^A_build_foo$', 'A_build_bar.*'], 'exclude': ['A_build_zap.*']}},
            {'A_build_zap.*'},
            {'^A_build_foo$', 'A_build_bar.*'},
            ['A_build_zap_123', 'A_build_zap456', 'A_build_foo', 'A_build_bar789'],
            [False, False, True, True],
            id="Include and exclude filters",
        ),
        pytest.param(
            {'project_a': {'include': ['^A_build_foo$']}},
            set(),
            {'^A_build_foo$'},
            ['A_build_foo', 'A_build_foo123', 'A_build_bar'],
            [True, False, False],
            id="Only include filter",
        ),
        pytest.param(
            {'project_a': {"exclude": ['A_build_zap.*']}},
            {'A_build_zap.*'},
            set(),
            ['A_build_zap123', 'A_build_zap_345', 'A_build_foo'],
            [False, False, True],
            id="Only exclude filter",
        ),
        pytest.param(
            {
                'project_c': {
                    'include': ['^C_build_foo$', 'C_build_bar.*'],
                    'exclude': ['^C_build_foo$', 'C_build_zap.*'],
                }
            },
            {'^C_build_foo$', 'C_build_zap.*'},
            {'C_build_bar.*'},
            ['C_build_bar', 'C_build_bar_123', 'C_build_foo567', 'C_build_foo_890', 'C_build_zap'],
            [True, True, False, False, False],
            id="Filter overlap",
        ),
        pytest.param(
            {
                'project_b': {'include': ['B_build_foo.*'], 'exclude': ['^B_build_bar$', 'B_build_zip']},
                'project_c': {
                    'include': ['^C_build_foo$', 'C_build_bar.*'],
                    'exclude': ['^C_build_foo$', 'C_build_zap.*'],
                },
            },
            {'^B_build_bar$', 'B_build_zip', '^C_build_foo$', 'C_build_zap.*'},
            {'B_build_foo.*', 'C_build_bar.*'},
            ['B_build_foo_abc', 'C_build_bar456', 'C_build_foo', 'C_build_foo_234', 'C_build_zap'],
            [True, True, False, False, False],
            id="Multiple projects and with filter overlap",
        ),
    ],
)
def test_projects_build_configs_filter(
    projects_config, expected_exclude, expected_include, sample_build_configs, should_include
):
    """
    Test that the build configurations filter is getting structured properly and filtering correctly
    """
    instance_config = {'server': 'localhost:8111', 'use_openmetrics': False, 'projects': projects_config}
    check = TeamCityCheck(CHECK_NAME, {}, [instance_config])

    exclude_filter, include_filter = construct_build_configs_filter(check)

    assert include_filter == expected_include
    assert exclude_filter == expected_exclude

    for i, sample in enumerate(sample_build_configs):
        included = should_include_build_config(check, sample)
        assert included == should_include[i]
