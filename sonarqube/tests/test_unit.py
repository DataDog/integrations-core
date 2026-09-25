# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from pathlib import Path
from typing import Any, Callable

from datadog_checks.base.utils.http_exceptions import HTTPClientError

from .common import HERE
from .metrics import WEB_METRICS


def _register_responses(
    fake_http_response: Callable[..., Any],
    endpoint: str,
    responses: list[tuple[str, str]],
) -> None:
    for path, fixture in responses:
        fixture_text = (Path(HERE) / 'api_responses' / fixture).read_text()
        if path == '/api/server/version':
            fake_http_response(f'{endpoint}{path}', fixture_text)
        else:
            fake_http_response(f'{endpoint}{path}', json_data=json.loads(fixture_text))


def test_service_check_critical(aggregator, dd_run_check, sonarqube_check, web_instance, fake_http):
    fake_http.register_response(
        'GET',
        f"{web_instance['web_endpoint']}/api/server/version",
        HTTPClientError('HTTP error'),
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_critical_when_the_api_answers_with_a_non_json_body(
    aggregator, dd_run_check, sonarqube_check, web_instance, fake_http_response
):
    # An SSO or reverse proxy in front of SonarQube answers a metrics search with 200 and an HTML login
    # page, so the failure surfaces while parsing the body rather than on the wire. The check reports
    # that as CRITICAL alongside the transport failures above.
    endpoint = web_instance['web_endpoint']
    _register_responses(fake_http_response, endpoint, [('/api/server/version', 'version')])
    fake_http_response(
        f'{endpoint}/api/metrics/search',
        '<html><body>Sign in</body></html>',
        headers={'Content-Type': 'text/html'},
        json_error=json.JSONDecodeError('Expecting value', '<html>', 0),
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance['tags'])

    dd_run_check(check)

    for metric_name in WEB_METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_ok_version_empty(aggregator, dd_run_check, sonarqube_check, web_instance, fake_http_response):
    endpoint = web_instance['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version_empty'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok(aggregator, dd_run_check, sonarqube_check, web_instance, fake_http_response):
    endpoint = web_instance['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_config_none(
    aggregator, dd_run_check, sonarqube_check, web_instance_config_none, fake_http_response
):
    endpoint = web_instance_config_none['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance_config_none)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance_config_none['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_exclude_metrics(
    aggregator, dd_run_check, sonarqube_check, web_instance_and_exclude_metrics, fake_http_response
):
    endpoint = web_instance_and_exclude_metrics['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance_and_exclude_metrics)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance_and_exclude_metrics['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include, fake_http_response
):
    endpoint = web_instance_with_autodiscovery_only_include['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/components/search', 'components_search'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_only_include)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include_metrics_empty(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include, fake_http_response
):
    endpoint = web_instance_with_autodiscovery_only_include['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_empty'),
            ('/api/components/search', 'components_search'),
            ('/api/measures/component', 'measures_component_empty'),
        ],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_only_include)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_exclude(
    aggregator,
    dd_run_check,
    sonarqube_check,
    web_instance_with_autodiscovery_include_all_and_exclude,
    fake_http_response,
):
    endpoint = web_instance_with_autodiscovery_include_all_and_exclude['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/components/search', 'components_search_with_tmp_p1'),
            ('/api/components/search', 'components_search_with_tmp_p2'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_exclude)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance_with_autodiscovery_include_all_and_exclude['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
        aggregator.assert_metric(
            metric_name, count=expect_count, tags=global_tags + ['project:org.sonarqube:sonarqube-scanner']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_limit(
    aggregator,
    dd_run_check,
    sonarqube_check,
    web_instance_with_autodiscovery_include_all_and_limit,
    fake_http_response,
):
    endpoint = web_instance_with_autodiscovery_include_all_and_limit['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/components/search', 'components_search_with_tmp_p1'),
            ('/api/components/search', 'components_search_with_tmp_p2'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_limit)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance_with_autodiscovery_include_all_and_limit['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
        aggregator.assert_metric(metric_name, count=expect_count, tags=global_tags + ['project:tmp_project'])
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_component_and_autodiscovery(
    aggregator,
    dd_run_check,
    sonarqube_check,
    web_instance_with_component_and_autodiscovery,
    fake_http_response,
):
    endpoint = web_instance_with_component_and_autodiscovery['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/measures/component', 'measures_component'),
            ('/api/components/search', 'components_search'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance_with_component_and_autodiscovery)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance_with_component_and_autodiscovery['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
        aggregator.assert_metric(metric_name, count=expect_count)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_config_none(
    aggregator,
    dd_run_check,
    sonarqube_check,
    web_instance_with_autodiscovery_config_none,
    fake_http_response,
):
    endpoint = web_instance_with_autodiscovery_config_none['web_endpoint']
    _register_responses(
        fake_http_response,
        endpoint,
        [
            ('/api/server/version', 'version'),
            ('/api/metrics/search', 'metrics_search_p_1'),
            ('/api/metrics/search', 'metrics_search_p_2'),
            ('/api/components/search', 'components_search'),
            ('/api/measures/component', 'measures_component'),
        ],
    )
    check = sonarqube_check(web_instance_with_autodiscovery_config_none)
    global_tags = ['endpoint:{}'.format(endpoint)]
    global_tags.extend(web_instance_with_autodiscovery_config_none['tags'])
    dd_run_check(check)
    for metric_name in WEB_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)
