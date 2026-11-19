# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientRequestError

from .common import HERE
from .metrics import WEB_METRICS

API_PATHS = {
    'version': '/api/server/version',
    'metrics_search': '/api/metrics/search',
    'measures_component': '/api/measures/component',
    'components_search': '/api/components/search',
}


def api_response(fixture):
    """Build a response whose `json()` behaves like a real response parsing the fixture."""
    with open(os.path.join(HERE, 'api_responses', fixture), 'rb') as f:
        content = f.read()
    try:
        return FakeHTTPResponse(content=content, json_result=json.loads(content))
    except json.JSONDecodeError as e:
        return FakeHTTPResponse(content=content, json_error=e)


def register_api_responses(fake_http, instance, fixtures):
    """Answer the check's requests in order, routing each fixture to the endpoint its name starts with."""
    for fixture in fixtures:
        path = next(path for prefix, path in API_PATHS.items() if fixture.startswith(prefix))
        fake_http.register_response('GET', instance['web_endpoint'] + path, api_response(fixture), once=True)


def test_service_check_critical(aggregator, dd_run_check, fake_http, sonarqube_check, web_instance):
    fake_http.register_response(
        'GET', web_instance['web_endpoint'] + API_PATHS['version'], HTTPClientRequestError('Req Exception')
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_critical_on_invalid_json(aggregator, dd_run_check, fake_http, sonarqube_check, web_instance):
    register_api_responses(fake_http, web_instance, ['version'])
    fake_http.register_response(
        'GET',
        web_instance['web_endpoint'] + API_PATHS['metrics_search'],
        FakeHTTPResponse(content=b'<html>', json_error=json.JSONDecodeError('Expecting value', '<html>', 0)),
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_ok_version_empty(aggregator, dd_run_check, fake_http, sonarqube_check, web_instance):
    register_api_responses(
        fake_http,
        web_instance,
        ['version_empty', 'metrics_search_p_1', 'metrics_search_p_2', 'measures_component'],
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok(aggregator, dd_run_check, fake_http, sonarqube_check, web_instance):
    register_api_responses(
        fake_http,
        web_instance,
        ['version', 'metrics_search_p_1', 'metrics_search_p_2', 'measures_component'],
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_config_none(
    aggregator, dd_run_check, fake_http, sonarqube_check, web_instance_config_none
):
    register_api_responses(
        fake_http,
        web_instance_config_none,
        ['version', 'metrics_search_p_1', 'metrics_search_p_2', 'measures_component'],
    )
    check = sonarqube_check(web_instance_config_none)
    global_tags = ['endpoint:{}'.format(web_instance_config_none['web_endpoint'])]
    global_tags.extend(web_instance_config_none['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_exclude_metrics(
    aggregator, dd_run_check, fake_http, sonarqube_check, web_instance_and_exclude_metrics
):
    register_api_responses(
        fake_http,
        web_instance_and_exclude_metrics,
        ['version', 'metrics_search_p_1', 'metrics_search_p_2', 'measures_component'],
    )
    check = sonarqube_check(web_instance_and_exclude_metrics)
    global_tags = ['endpoint:{}'.format(web_instance_and_exclude_metrics['web_endpoint'])]
    global_tags.extend(web_instance_and_exclude_metrics['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include(
    aggregator, dd_run_check, fake_http, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_only_include,
        ['version', 'metrics_search_p_1', 'metrics_search_p_2', 'components_search', 'measures_component'],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_only_include)
    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include_metrics_empty(
    aggregator, dd_run_check, fake_http, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_only_include,
        ['version', 'metrics_search_empty', 'components_search', 'measures_component_empty'],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_only_include)
    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_exclude(
    aggregator, dd_run_check, fake_http, sonarqube_check, web_instance_with_autodiscovery_include_all_and_exclude
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_include_all_and_exclude,
        [
            'version',
            'metrics_search_p_1',
            'metrics_search_p_2',
            'components_search_with_tmp_p1',
            'components_search_with_tmp_p2',
            'measures_component',
        ],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_exclude)
    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_include_all_and_exclude['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_include_all_and_exclude['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
        aggregator.assert_metric(
            metric_name, count=expect_count, tags=global_tags + ['project:org.sonarqube:sonarqube-scanner']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_limit(
    aggregator, dd_run_check, fake_http, sonarqube_check, web_instance_with_autodiscovery_include_all_and_limit
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_include_all_and_limit,
        [
            'version',
            'metrics_search_p_1',
            'metrics_search_p_2',
            'components_search_with_tmp_p1',
            'components_search_with_tmp_p2',
            'measures_component',
        ],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_limit)
    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_include_all_and_limit['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_include_all_and_limit['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
        aggregator.assert_metric(metric_name, count=expect_count, tags=global_tags + ['project:tmp_project'])
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_component_and_autodiscovery(
    aggregator, dd_run_check, fake_http, sonarqube_check, web_instance_with_component_and_autodiscovery
):
    register_api_responses(
        fake_http,
        web_instance_with_component_and_autodiscovery,
        [
            'version',
            'metrics_search_p_1',
            'metrics_search_p_2',
            'measures_component',
            'components_search',
            'measures_component',
        ],
    )
    check = sonarqube_check(web_instance_with_component_and_autodiscovery)
    global_tags = ['endpoint:{}'.format(web_instance_with_component_and_autodiscovery['web_endpoint'])]
    global_tags.extend(web_instance_with_component_and_autodiscovery['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
        aggregator.assert_metric(metric_name, count=expect_count)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_config_none(
    aggregator, dd_run_check, fake_http, sonarqube_check, web_instance_with_autodiscovery_config_none
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_config_none,
        ['version', 'metrics_search_p_1', 'metrics_search_p_2', 'components_search', 'measures_component'],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_config_none)
    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_config_none['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_config_none['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)
