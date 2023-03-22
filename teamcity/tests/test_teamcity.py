# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest
from mock import ANY, patch
from six import PY2

from datadog_checks.teamcity.constants import (
    SERVICE_CHECK_BUILD_PROBLEMS,
    SERVICE_CHECK_BUILD_STATUS,
    SERVICE_CHECK_TEST_RESULTS,
)
from datadog_checks.teamcity.teamcity_rest import TeamCityRest

from .common import (
    BUILD_STATS_METRICS,
    BUILD_TAGS,
    EXPECTED_SERVICE_CHECK_TEST_RESULTS,
    LEGACY_REST_INSTANCE,
    USE_OPENMETRICS,
)

pytestmark = [
    pytest.mark.skipif(USE_OPENMETRICS, reason='Tests not available in OpenMetrics version of check'),
    pytest.mark.integration,
    pytest.mark.usefixtures('dd_environment'),
]

BUILD_TAGS = BUILD_TAGS + ['instance_name:SampleProject_Build'] if PY2 else BUILD_TAGS


def test_build_event(dd_run_check, aggregator, rest_instance):
    instance = deepcopy(rest_instance)
    flags = {'build_config_metrics': False, 'tests_health_check': False, 'build_problem_health_check': False}
    instance.update(flags)

    check = TeamCityRest('teamcity', {}, [instance])
    event_tags = BUILD_TAGS
    dd_run_check(check)
    assert not len(aggregator.metric_names)
    aggregator.assert_event(
        event_type='build',
        host='buildhost42.dtdg.co',
        msg_text='Build Number: 2\nDeployed To: buildhost42.dtdg.co\n\n'
        'More Info: http://localhost:8111/viewLog.html?buildId=1&buildTypeId=SampleProject_Build',
        msg_title='Build for SampleProject_Build successful',
        source_type_name='teamcity',
        alert_type='success',
        tags=event_tags + ['build_id:2', 'build_number:2', 'build', 'type:build'],
        count=1,
    )

    dd_run_check(check)
    aggregator.assert_event(msg_title="", msg_text="", count=0)


@pytest.mark.parametrize(
    'extra_config, expected_http_kwargs',
    [
        pytest.param({'ssl_validation': True}, {'verify': True}, id="legacy ssl config True"),
        pytest.param({'ssl_validation': False}, {'verify': False}, id="legacy ssl config False"),
        pytest.param({}, {'verify': True}, id="legacy ssl config unset"),
    ],
)
def test_config(dd_run_check, extra_config, expected_http_kwargs):
    instance = deepcopy(LEGACY_REST_INSTANCE)
    instance.update(extra_config)
    check = TeamCityRest('teamcity', {}, [instance])

    with patch('datadog_checks.base.utils.http.requests.get') as r:
        dd_run_check(check)

        http_wargs = {
            'auth': ANY,
            'cert': ANY,
            'headers': ANY,
            'proxies': ANY,
            'timeout': ANY,
            'verify': ANY,
            'allow_redirects': ANY,
        }
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
        pytest.param(
            {'projects': {'project_id': {}}, 'build_configuration': 'build_config_id'},
            'Only one of `projects` or `build_configuration` may be configured, not both.',
            id="Redundant configs",
        ),
    ],
)
def test_validate_config(dd_run_check, build_config, expected_error, caplog):
    """
    Test that the `build_configuration` config options are properly configured in Python 2 prior to running check.
    Note: The properly configured test cases would be expected to have a `Failed to establish a new connection`
    exception.
    """
    caplog.clear()
    config = {'server': 'server.name', 'use_openmetrics': False}

    instance = deepcopy(config)
    instance.update(build_config)

    check = TeamCityRest('teamcity', {}, [instance])

    if PY2 and instance.get('projects'):
        expected_error = (
            '`projects` option is not supported for Python 2. '
            'Use the `build_configuration` option or upgrade to Python 3.'
        )

    with pytest.raises(Exception, match=expected_error):
        dd_run_check(check)


def test_collect_build_stats(dd_run_check, aggregator, rest_instance, teamcity_rest_check, caplog):
    instance = deepcopy(rest_instance)
    flags = {'collect_events': False, 'tests_health_check': False, 'build_problem_health_check': False}
    instance.update(flags)
    check = teamcity_rest_check(instance)
    dd_run_check(check)

    for metric in BUILD_STATS_METRICS:
        metric_name = metric['name']
        expected_val = metric['value']
        expected_tags = metric['tags'] if not PY2 else metric['tags'] + ['instance_name:SampleProject_Build']

        aggregator.assert_metric(metric_name, tags=expected_tags, value=expected_val)

    aggregator.assert_all_metrics_covered()


def test_collect_test_results(dd_run_check, aggregator, rest_instance, teamcity_rest_check):
    instance = deepcopy(rest_instance)
    flags = {'collect_events': False, 'build_config_metrics': False, 'build_problem_health_check': False}
    instance.update(flags)
    check = teamcity_rest_check(instance)

    dd_run_check(check)

    for res in EXPECTED_SERVICE_CHECK_TEST_RESULTS:
        expected_status = res['value']
        expected_tests_tags = res['tags'] if not PY2 else res['tags'] + ['instance_name:SampleProject_Build']
        aggregator.assert_service_check(
            'teamcity.{}'.format(SERVICE_CHECK_TEST_RESULTS), status=expected_status, tags=expected_tests_tags
        )


def test_collect_build_problems(dd_run_check, aggregator, rest_instance, teamcity_rest_check):
    instance = deepcopy(rest_instance)
    flags = {
        'collect_events': False,
        'build_config_metrics': False,
        'tests_health_check': False,
    }
    instance.update(flags)
    expected_tags = BUILD_TAGS + ['problem_identity:python_build_error_identity', 'problem_type:TC_EXIT_CODE']
    check = teamcity_rest_check(instance)

    dd_run_check(check)

    aggregator.assert_service_check(
        'teamcity.{}'.format(SERVICE_CHECK_BUILD_PROBLEMS),
        count=1,
        tags=expected_tags,
        status=TeamCityRest.CRITICAL,
    )
    aggregator.assert_service_check(
        'teamcity.{}'.format(SERVICE_CHECK_BUILD_PROBLEMS),
        count=1,
        tags=BUILD_TAGS,
        status=TeamCityRest.OK,
    )


def test_handle_empty_builds(dd_run_check, aggregator, empty_builds_rest_instance, teamcity_rest_check):
    check = teamcity_rest_check(empty_builds_rest_instance)
    dd_run_check(check)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_BUILD_STATUS), count=0)
