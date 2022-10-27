# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from copy import deepcopy

import mock
import pytest
from mock import ANY, patch

from datadog_checks.teamcity import TeamCityCheck
from datadog_checks.teamcity.constants import (
    SERVICE_CHECK_BUILD_PROBLEMS,
    SERVICE_CHECK_BUILD_STATUS,
    SERVICE_CHECK_TEST_RESULTS,
)

from .common import (
    BUILD_STATS_METRICS,
    BUILD_TAGS,
    EXPECTED_SERVICE_CHECK_TEST_RESULTS,
    LEGACY_BUILD_TAGS,
    LEGACY_INSTANCE,
    NEW_FAILED_BUILD,
    NEW_SUCCESSFUL_BUILD,
    USE_OPENMETRICS,
    get_fixture_path,
)

pytestmark = [
    pytest.mark.skipif(USE_OPENMETRICS, reason='Tests not available in OpenMetrics version of check'),
    pytest.mark.integration,
]


def test_build_event(dd_run_check, aggregator, legacy_instance):
    legacy_instance['build_config_metrics'] = False
    legacy_instance['tests_health_check'] = False
    legacy_instance['build_problem_health_check'] = False

    teamcity = TeamCityCheck('teamcity', {}, [legacy_instance])

    responses = json.load(open(get_fixture_path('event_responses.json'), 'r'))

    json_responses = [
        responses['build_config'],
        responses['build_config_settings'],
        responses['last_build'],
        responses['new_builds'],
        responses['server_details'],
    ]

    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.json.side_effect = json_responses
        req.get.return_value = mock_resp
        teamcity.check(legacy_instance)

    assert len(aggregator.metric_names) == 0
    aggregator.assert_event(
        event_type='build',
        host='buildhost42.dtdg.co',
        msg_text='Build Number: 1\nDeployed To: buildhost42.dtdg.co\n\nMore Info: '
        'http://localhost:8111/viewLog.html?buildId=1&buildTypeId=SampleProject_Build',
        msg_title='Build for Legacy test build successful',
        source_type_name='teamcity',
        alert_type='success',
        tags=LEGACY_BUILD_TAGS + ['build_id:1', 'build_number:1', 'build', 'type:build'],
        count=1,
    )

    aggregator.reset()

    # One more check should not create any more events
    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.json.side_effect = [responses['server_details'], responses['no_new_builds']]
        req.get.return_value = mock_resp
        teamcity.check(legacy_instance)

    aggregator.assert_event(msg_title="", msg_text="", count=0)


@pytest.mark.parametrize(
    'extra_config, expected_http_kwargs',
    [
        pytest.param({'ssl_validation': True}, {'verify': True}, id="legacy ssl config True"),
        pytest.param({'ssl_validation': False}, {'verify': False}, id="legacy ssl config False"),
        pytest.param({}, {'verify': True}, id="legacy ssl config unset"),
    ],
)
def test_config(extra_config, expected_http_kwargs):
    instance = deepcopy(LEGACY_INSTANCE)
    instance.update(extra_config)
    check = TeamCityCheck('teamcity', {}, [instance])

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
    'build_config, expected_error',
    [
        pytest.param(
            {'projects': {'project_id': {}}}, 'Failed to establish a new connection', id="One `projects` config"
        ),
        pytest.param(
            {'build_configuration': 'build_config_id'},
            'Failed to establish a new connection',
            id="One `build_configurations` config",
        ),
        pytest.param({}, '`projects` must be configured', id="Missing projects config"),
        pytest.param(
            {'projects': {'project_id': {}}, 'build_configuration': 'build_config_id'},
            'Only one of `projects` or `build_configuration` may be configured, not both.',
            id="Redundant configs",
        ),
    ],
)
def test_validate_config(dd_run_check, build_config, expected_error, caplog):
    """
    Test that the `projects` and `build_configuration` config options are properly configured prior to running check.
    Note: The properly configured test cases would be expected to have a `Failed to establish a new connection`
    exception.
    """
    caplog.clear()
    config = {'server': 'server.name', 'use_openmetrics': False}

    instance = deepcopy(config)
    instance.update(build_config)

    check = TeamCityCheck('teamcity', {}, [instance])

    with pytest.raises(Exception) as e:
        dd_run_check(check)

    assert expected_error in str(e.value)


def test_collect_build_stats(aggregator, mock_http_response, instance, teamcity_check):
    check = teamcity_check(instance)
    check.build_tags = BUILD_TAGS

    mock_http_response(file_path=get_fixture_path("build_stats.json"))
    check._collect_build_stats(NEW_SUCCESSFUL_BUILD)

    for metric in BUILD_STATS_METRICS:
        metric_name = metric['name']
        expected_val = metric['value']
        expected_stats_tags = metric['tags']
        aggregator.assert_metric(metric_name, tags=expected_stats_tags, value=expected_val)

    aggregator.assert_all_metrics_covered()


def test_collect_test_results(aggregator, mock_http_response, instance, teamcity_check):
    check = teamcity_check(instance)
    check.build_tags = BUILD_TAGS

    mock_http_response(file_path=get_fixture_path("test_occurrences.json"))
    check._collect_test_results(NEW_SUCCESSFUL_BUILD)

    for res in EXPECTED_SERVICE_CHECK_TEST_RESULTS:
        expected_status = res['value']
        expected_tests_tags = res['tags']
        aggregator.assert_service_check(
            'teamcity.{}'.format(SERVICE_CHECK_TEST_RESULTS), status=expected_status, tags=expected_tests_tags
        )


def test_collect_build_problems(aggregator, mock_http_response, instance, teamcity_check):
    mock_http_response(file_path=get_fixture_path('build_problems.json'))
    check = teamcity_check(instance)
    check.build_tags = BUILD_TAGS
    expected_tags = BUILD_TAGS + ['problem_identity:python_build_error_identity', 'problem_type:TC_EXIT_CODE']

    check._collect_build_problems(NEW_FAILED_BUILD)

    aggregator.assert_service_check(
        'teamcity.{}'.format(SERVICE_CHECK_BUILD_PROBLEMS),
        count=1,
        tags=expected_tags,
        status=TeamCityCheck.CRITICAL,
    )


def test_handle_empty_builds(aggregator, mock_http_response, instance, legacy_instance, teamcity_check):
    instances = [instance, legacy_instance]

    for inst in instances:
        check = teamcity_check(inst)
        mock_http_response(file_path=get_fixture_path("init_no_builds.json"))
        check.check(inst)
        aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_BUILD_STATUS), count=0)

        aggregator.reset()
