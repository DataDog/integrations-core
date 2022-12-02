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
    # Given
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = requests.exceptions.RequestException('Req Exception')
        check = sonarqube_check(web_instance)
        global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
        global_tags.extend(web_instance['tags'])
        # When
        dd_run_check(check)
        # Then
        for metric_name in WEB_METRICS:
            assert len(aggregator.metrics(metric_name)) == 0
        aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_ok_version_empty(aggregator, dd_run_check, sonarqube_check, web_instance):
    # Given
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
        # When
        dd_run_check(check)
        # Then
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok(aggregator, dd_run_check, sonarqube_check, web_instance):
    # Given
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
        # When
        dd_run_check(check)
        # Then
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    # Given
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
        # When
        dd_run_check(check)
        # Then
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include_metrics_empty(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    # Given
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
        # When
        dd_run_check(check)
        # Then
        for metric_name in WEB_METRICS:
            assert len(aggregator.metrics(metric_name)) == 0
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_exclude(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_include_all_and_exclude
):
    # Given
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_exclude)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_include_all_and_exclude['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_include_all_and_exclude['tags'])
        # When
        dd_run_check(check)
        # Then
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_limit(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_include_all_and_limit
):
    # Given
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_limit)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_include_all_and_limit['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_include_all_and_limit['tags'])
        # When
        dd_run_check(check)
        # Then
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)
