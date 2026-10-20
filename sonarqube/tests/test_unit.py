# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientError

from .common import HERE
from .metrics import WEB_METRICS

API_PATHS = {
    'version': '/api/server/version',
    'metrics_search': '/api/metrics/search',
    'components_search': '/api/components/search',
    'measures_component': '/api/measures/component',
}


def register_api_responses(fake_http, instance, *fixture_names):
    """Register API fixture files in the order the check requests them."""
    for name in fixture_names:
        path = next(path for prefix, path in API_PATHS.items() if name.startswith(prefix))
        with open(os.path.join(HERE, 'api_responses', name), 'rb') as f:
            content = f.read()
        # The version endpoint answers with plain text, every other endpoint with JSON.
        response = (
            FakeHTTPResponse(content=content)
            if path == API_PATHS['version']
            else FakeHTTPResponse(content=content, json_result=json.loads(content))
        )
        fake_http.register_response('GET', instance['web_endpoint'] + path, response)


def test_service_check_critical(fake_http, aggregator, dd_run_check, sonarqube_check, web_instance):
    fake_http.register_response(
        'GET', f"{web_instance['web_endpoint']}/api/server/version", HTTPClientError('HTTP error')
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_critical_when_the_api_answers_with_a_non_json_body(
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance
):
    # An SSO or reverse proxy in front of SonarQube answers a metrics search with 200 and an HTML login
    # page, so the failure surfaces while parsing the body rather than on the wire. The check reports
    # that as CRITICAL alongside the transport failures above.
    register_api_responses(fake_http, web_instance, 'version')
    fake_http.register_response(
        'GET',
        f"{web_instance['web_endpoint']}/api/metrics/search",
        FakeHTTPResponse(
            content=b'<html><body>Sign in</body></html>',
            headers={'Content-Type': 'text/html'},
            json_error=json.JSONDecodeError('Expecting value', '<html><body>Sign in</body></html>', 0),
        ),
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])

    dd_run_check(check)

    for metric_name in WEB_METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_ok_version_empty(fake_http, aggregator, dd_run_check, sonarqube_check, web_instance):
    register_api_responses(
        fake_http, web_instance, 'version_empty', 'metrics_search_p_1', 'metrics_search_p_2', 'measures_component'
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok(fake_http, aggregator, dd_run_check, sonarqube_check, web_instance):
    register_api_responses(
        fake_http, web_instance, 'version', 'metrics_search_p_1', 'metrics_search_p_2', 'measures_component'
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_config_none(
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance_config_none
):
    register_api_responses(
        fake_http, web_instance_config_none, 'version', 'metrics_search_p_1', 'metrics_search_p_2', 'measures_component'
    )
    check = sonarqube_check(web_instance_config_none)
    global_tags = ['endpoint:{}'.format(web_instance_config_none['web_endpoint'])]
    global_tags.extend(web_instance_config_none['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_exclude_metrics(
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance_and_exclude_metrics
):
    register_api_responses(
        fake_http,
        web_instance_and_exclude_metrics,
        'version',
        'metrics_search_p_1',
        'metrics_search_p_2',
        'measures_component',
    )
    check = sonarqube_check(web_instance_and_exclude_metrics)
    global_tags = ['endpoint:{}'.format(web_instance_and_exclude_metrics['web_endpoint'])]
    global_tags.extend(web_instance_and_exclude_metrics['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include(
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_only_include,
        'version',
        'metrics_search_p_1',
        'metrics_search_p_2',
        'components_search',
        'measures_component',
    )
    check = sonarqube_check(web_instance_with_autodiscovery_only_include)
    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include_metrics_empty(
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_only_include,
        'version',
        'metrics_search_empty',
        'components_search',
        'measures_component_empty',
    )
    check = sonarqube_check(web_instance_with_autodiscovery_only_include)
    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_exclude(
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_include_all_and_exclude
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_include_all_and_exclude,
        'version',
        'metrics_search_p_1',
        'metrics_search_p_2',
        'components_search_with_tmp_p1',
        'components_search_with_tmp_p2',
        'measures_component',
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
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_include_all_and_limit
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_include_all_and_limit,
        'version',
        'metrics_search_p_1',
        'metrics_search_p_2',
        'components_search_with_tmp_p1',
        'components_search_with_tmp_p2',
        'measures_component',
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
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance_with_component_and_autodiscovery
):
    register_api_responses(
        fake_http,
        web_instance_with_component_and_autodiscovery,
        'version',
        'metrics_search_p_1',
        'metrics_search_p_2',
        'measures_component',
        'components_search',
        'measures_component',
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
    fake_http, aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_config_none
):
    register_api_responses(
        fake_http,
        web_instance_with_autodiscovery_config_none,
        'version',
        'metrics_search_p_1',
        'metrics_search_p_2',
        'components_search',
        'measures_component',
    )
    check = sonarqube_check(web_instance_with_autodiscovery_config_none)
    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_config_none['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_config_none['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)
