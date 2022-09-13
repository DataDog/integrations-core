# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest
from mock import ANY, MagicMock, patch

from datadog_checks.teamcity import TeamCityCheck

from .common import BUILD_STATS_METRICS, CHECK_NAME, CONFIG, TEST_OCCURRENCES_METRICS, get_fixture_path


@pytest.mark.integration
def test_build_event(aggregator):
    teamcity = TeamCityCheck(CHECK_NAME, {}, [CONFIG])

    with patch('datadog_checks.base.utils.http.requests.get', get_mock_first_build):
        teamcity.check(CONFIG['instances'][0])

    assert len(aggregator.metric_names) == 0
    assert len(aggregator.events) == 0
    aggregator.reset()

    with patch('datadog_checks.base.utils.http.requests.get', get_mock_one_more_build):
        teamcity.check(CONFIG['instances'][0])

    events = aggregator.events
    assert len(events) == 1
    assert events[0]['msg_title'] == "Build for One test build successful"
    assert (
        events[0]['msg_text']
        == "Build Number: 2\nDeployed To: buildhost42.dtdg.co\n\nMore Info: "
        + "http://localhost:8111/viewLog.html?buildId=2&buildTypeId=TestProject_TestBuild"
    )
    assert events[0]['tags'] == ['build', 'one:tag', 'one:test']
    assert events[0]['host'] == "buildhost42.dtdg.co"
    aggregator.reset()

    # One more check should not create any more events
    with patch('datadog_checks.base.utils.http.requests.get', get_mock_one_more_build):
        teamcity.check(CONFIG['instances'][0])

    assert len(aggregator.events) == 0


def get_mock_first_build(url, *args, **kwargs):
    mock_resp = MagicMock()
    if 'sinceBuild' in url:
        # looking for new builds
        json = {
            "count": 0,
            "href": (
                "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS"
            ),
        }
    else:
        json = {
            "count": 1,
            "href": "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,count:1",
            "nextHref": "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,count:1,start:1",
            "build": [
                {
                    "id": 1,
                    "buildTypeId": "TestProject_TestBuild",
                    "number": "1",
                    "status": "SUCCESS",
                    "state": "finished",
                    "href": "/guestAuth/app/rest/builds/id:1",
                    "webUrl": "http://localhost:8111/viewLog.html?buildId=1&buildTypeId=TestProject_TestBuild",
                }
            ],
        }

    mock_resp.json.return_value = json
    return mock_resp


def get_mock_one_more_build(url, *args, **kwargs):
    mock_resp = MagicMock()
    json = {}

    if 'sinceBuild:id:1' in url:
        json = {
            "count": 1,
            "href": "/guestAuth/app/rest/builds/?"
            + "locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS",
            "build": [
                {
                    "id": 2,
                    "buildTypeId": "TestProject_TestBuild",
                    "number": "2",
                    "status": "SUCCESS",
                    "state": "finished",
                    "href": "/guestAuth/app/rest/builds/id:2",
                    "webUrl": "http://localhost:8111/viewLog.html?buildId=2&buildTypeId=TestProject_TestBuild",
                }
            ],
        }
    elif 'sinceBuild:id:2' in url:
        json = {
            "count": 0,
            "href": (
                "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:2,status:SUCCESS"
            ),
        }

    mock_resp.json.return_value = json
    return mock_resp


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        ("legacy ssl config True", {'ssl_validation': True}, {'verify': True}),
        ("legacy ssl config False", {'ssl_validation': False}, {'verify': False}),
        ("legacy ssl config unset", {}, {'verify': True}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(CONFIG['instances'][0])
    instance.update(extra_config)
    check = TeamCityCheck(CHECK_NAME, {}, [instance])

    with patch('datadog_checks.base.utils.http.requests.get') as r:
        check.check(instance)

        http_wargs = dict(
            auth=ANY,
            cert=ANY,
            headers=ANY,
            proxies=ANY,
            timeout=ANY,
            verify=ANY,
            allow_redirects=ANY,
        )
        http_wargs.update(expected_http_kwargs)

        r.assert_called_with(ANY, **http_wargs)


@pytest.mark.parametrize(
    'file_name, method, expected_metrics',
    [
        pytest.param("build_stats.json", "_collect_build_stats", BUILD_STATS_METRICS, id="Build config metrices"),
        pytest.param(
            "test_occurrences.json", "_collect_test_results", TEST_OCCURRENCES_METRICS, id="Test result metrics"
        ),
    ],
)
def test_collect_rest_metrics(
    aggregator, mock_http_response, tcv2_instance, file_name, method, expected_metrics, check
):
    mock_http_response(file_path=get_fixture_path(file_name))
    check = check(tcv2_instance)
    mock_new_build = {
        'id': 232,
        'buildTypeId': 'TeamcityPythonFork_Build',
        'number': '11',
        'status': 'SUCCESS',
        'state': 'finished',
        'branchName': 'main',
        'defaultBranch': True,
        'href': '/guestAuth/app/rest/builds/id:232',
        'webUrl': 'http://localhost:8111/viewLog.html?buildId=232&buildTypeId=TeamcityPythonFork_Build',
        'finishOnAgentDate': '20220913T210820+0000',
    }
    method = getattr(check, method)
    method(mock_new_build)

    for metric_name in expected_metrics:
        aggregator.assert_metric(metric_name)


def test_build_problem_service_checks(aggregator, mock_http_response, tcv2_instance, check):
    mock_http_response(file_path=get_fixture_path('build_problems.json'))
    check = check(tcv2_instance)
    mock_new_build = {
        'id': 233,
        'buildTypeId': 'TeamcityPythonFork_FailedBuild',
        'number': '12',
        'status': 'FAILURE',
        'state': 'finished',
        'branchName': 'main',
        'defaultBranch': True,
        'href': '/guestAuth/app/rest/builds/id:233',
        'webUrl': 'http://localhost:8111/viewLog.html?buildId=233&buildTypeId=TeamcityPythonFork_FailedBuild',
        'finishOnAgentDate': '20220913T210826+0000',
    }

    check._collect_build_problems(mock_new_build)

    aggregator.assert_service_check(
        'teamcity.build_problem',
        count=1,
        tags=[
            'build_config:None',
            'build_env:test',
            'build_id:233',
            'build_number:12',
            'instance_name:TeamCityV2 test build',
            'problem_identity:python_build_error_identity',
            'problem_type:TC_EXIT_CODE',
            'server:http://localhost:8111',
            'test_tag:ci_builds',
            'type:build',
        ],
        status=check.WARNING,
    )
