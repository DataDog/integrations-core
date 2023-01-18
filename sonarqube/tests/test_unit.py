# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import requests

from datadog_checks.dev.http import MockResponse

from .common import HERE
from .metrics import WEB_METRICS

pytestmark = [pytest.mark.unit]


def test_service_check_critical(aggregator, dd_run_check, sonarqube_check, web_instance):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = requests.exceptions.RequestException('Req Exception')
        check = sonarqube_check(web_instance)
        global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
        global_tags.extend(web_instance['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            assert len(aggregator.metrics(metric_name)) == 0
        aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_ok_version_empty(aggregator, dd_run_check, sonarqube_check, web_instance):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version_empty')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance)
        global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
        global_tags.extend(web_instance['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok(aggregator, dd_run_check, sonarqube_check, web_instance):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance)
        global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
        global_tags.extend(web_instance['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_config_none(aggregator, dd_run_check, sonarqube_check, web_instance_config_none):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_config_none)
        global_tags = ['endpoint:{}'.format(web_instance_config_none['web_endpoint'])]
        global_tags.extend(web_instance_config_none['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_exclude_metrics(
    aggregator, dd_run_check, sonarqube_check, web_instance_and_exclude_metrics
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_and_exclude_metrics)
        global_tags = ['endpoint:{}'.format(web_instance_and_exclude_metrics['web_endpoint'])]
        global_tags.extend(web_instance_and_exclude_metrics['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_only_include)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include_metrics_empty(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_empty')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component_empty')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_only_include)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            assert len(aggregator.metrics(metric_name)) == 0
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_exclude(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_include_all_and_exclude
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp_p1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp_p2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_exclude)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_include_all_and_exclude['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_include_all_and_exclude['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(
                metric_name, count=1, tags=global_tags + ['project:org.sonarqube:sonarqube-scanner']
            )
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_limit(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_include_all_and_limit
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp_p1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp_p2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_limit)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_include_all_and_limit['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_include_all_and_limit['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name, count=1, tags=global_tags + ['project:tmp_project'])
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_component_and_autodiscovery(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_component_and_autodiscovery
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_component_and_autodiscovery)
        global_tags = ['endpoint:{}'.format(web_instance_with_component_and_autodiscovery['web_endpoint'])]
        global_tags.extend(web_instance_with_component_and_autodiscovery['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name, count=1)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_config_none(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_config_none
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_config_none)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_config_none['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_config_none['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)
