import re
from random import randrange

import mock
import pytest

from .common import HOST, METRICS, PORT

pytestmark = [pytest.mark.unit]


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_service_check_ok(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'components': {},
    }
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_tags(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'components': {},
        'tags': [
            'tag1:foo',
            'tag2:bar',
        ],
    }
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check(
        'sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000', 'tag1:foo', 'tag2:bar']
    )


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_empty_components(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'components': {},
    }
    mock_api.return_value.get_projects.return_value = []
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_metrics.assert_not_called()
    mock_api.return_value.get_measures.assert_not_called()
    for metric in METRICS:
        assert len(aggregator.metrics(metric)) == 0
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_no_tag(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'components': {
            'project1': {},
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_default_tag(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'default_tag': 'project',
        'components': {
            'project1': {},
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'project:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_default_tag_overwritten(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'default_tag': 'project',
        'components': {
            'project1': {
                'tag': 'project1-tag',
            },
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'project1-tag:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_project_tag(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'components': {
            'project1': {
                'tag': 'project1-tag',
            },
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'project1-tag:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_components_with_default_exclude(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'default_exclude': [
            'category2.',
        ],
        'components': {
            'project1': {},
        },
    }
    mock_api.return_value.get_version.return_value = '1.2.3.12345'
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [
        metric for metric in METRICS if re.search('^category2\\.', metric) or re.search('^.*\\.new_.*', metric)
    ]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_components_with_exclude(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'default_exclude': [
            'category1.',
        ],
        'components': {
            'project1': {
                'exclude': [
                    'category2.',
                ],
            },
        },
    }
    mock_api.return_value.get_version.return_value = '1.2.3.12345'
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [
        metric for metric in METRICS if re.search('^category2\\.', metric) or re.search('^.*\\.new_.*', metric)
    ]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_components_with_default_include(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'default_include': [
            'category2.',
        ],
        'components': {
            'project1': {},
        },
    }
    mock_api.return_value.get_version.return_value = '1.2.3.12345'
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [
        metric for metric in METRICS if re.search('^category2\\.', metric) and metric not in excluded_metrics
    ]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_components_with_include(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'default_include': [
            'category1.',
        ],
        'components': {
            'project1': {
                'include': [
                    'category2.',
                ],
            },
        },
    }
    mock_api.return_value.get_version.return_value = '1.2.3.12345'
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [
        metric for metric in METRICS if re.search('^category2\\.', metric) and metric not in excluded_metrics
    ]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])


@mock.patch("datadog_checks.sonarqube.check.SonarqubeAPI")
def test_components_with_include_and_exclude(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    instance = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'components': {
            'project1': {
                'include': [
                    'category1.',
                ],
                'exclude': [
                    'category3.',
                ],
            },
        },
    }
    mock_api.return_value.get_version.return_value = '1.2.3.12345'
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [
        metric for metric in METRICS if re.search('^category3\\.', metric) or re.search('^.*\\.new_.*', metric)
    ]
    included_metrics = [
        metric for metric in METRICS if re.search('^category1\\.', metric) and metric not in excluded_metrics
    ]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [("{}".format(metric.split('.')[1]), value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(instance)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', ["{}".format(metric.split('.')[1]) for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            'sonarqube.{}'.format(metric), value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000'])
