import re
from random import randrange

import mock
import pytest
import requests

from .common import HOST, METRICS, PORT

pytestmark = [pytest.mark.unit]


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_service_check_critical(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {},
    }
    mock_api.return_value.get_version.side_effect = requests.exceptions.RequestException('Req Exception')
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    for metric_name in METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check(
        'sonarqube.api_access', status=check.CRITICAL, tags=['endpoint:http://localhost:9000']
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_version_none(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {},
    }
    mock_api.return_value.get_version.return_value = None
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    for metric_name in METRICS:
        assert len(aggregator.metrics(metric_name)) == 0
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_service_check_ok(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {},
    }
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_tags(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {},
        'tags': [
            'tag1:foo',
            'tag2:bar',
        ],
    }
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check(
        'sonarqube.api_access', status=check.OK, tags=['endpoint:http://localhost:9000', 'tag1:foo', 'tag2:bar']
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_empty_projects(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {},
    }
    mock_api.return_value.get_projects.return_value = []
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_metrics.assert_not_called()
    mock_api.return_value.get_measures.assert_not_called()
    for metric in METRICS:
        assert len(aggregator.metrics(metric)) == 0
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_default_tag_with_projects_type_dict(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'default_tag': 'project',
            'keys': [
                {
                    'project1': {},
                },
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'project:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_default_tag_with_projects_type_str(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'default_tag': 'project',
            'keys': [
                'project1',
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'project:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_default_tag_overwritten(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'default_tag': 'project',
            'keys': [
                {
                    'project1': {'tag': 'project1-tag'},
                },
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'project1-tag:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_project_tag(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'keys': [
                {
                    'project1': {'tag': 'project1-tag'},
                },
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'project1-tag:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_default_metrics_limit(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'default_metrics_limit': 2,
            'keys': [
                {
                    'project1': {},
                },
                'project1',
                'project3',
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics][0:2]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_default_metrics_include(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'default_metrics_include': [
                '^category2\\..*',
            ],
            'keys': [
                {
                    'project1': {},
                },
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [
        metric for metric in METRICS if re.search('^category2\\.', metric) and metric not in excluded_metrics
    ]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_default_metrics_exclude(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'default_metrics_exclude': [
                '^category2\\..*',
            ],
            'keys': [
                {
                    'project1': {},
                },
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^category2\\.', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_default_metrics_include_and_exclude(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'default_metrics_include': [
                '^category1\\..*',
            ],
            'default_metrics_exclude': [
                '^category2\\..*',
            ],
            'keys': [
                {
                    'project1': {},
                },
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^category2\\.', metric)]
    included_metrics = [
        metric for metric in METRICS if re.search('^category1\\.', metric) and metric not in excluded_metrics
    ]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_metrics_limit(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'keys': [
                {
                    'project1': {
                        'metrics': {
                            'discovery': {'limit': 2},
                        },
                    },
                },
            ],
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics][0:2]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_unexpected_measure(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'keys': [
                {
                    'project1': {
                        'metrics': {
                            'discovery': {'limit': 2},
                        },
                    },
                },
            ]
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics][0:2]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values] + [
        ('unexpected_measure', 99)
    ]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_called_with(
        'project1', [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}', value=value, tags=['endpoint:http://localhost:9000', 'component:project1']
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_projects_discovery(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'discovery': {
                'include': ['^project.*'],
            },
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1', 'project2', 'tmp_project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_has_calls(
        [
            mock.call(
                'project1',
                [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values],
            ),
            mock.call(
                'project2',
                [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values],
            ),
        ]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}',
            value=value,
            tags=[
                'endpoint:http://localhost:9000',
                'component:project1',
            ],
        )
        aggregator.assert_metric(
            f'sonarqube.{metric}',
            value=value,
            tags=[
                'endpoint:http://localhost:9000',
                'component:project2',
            ],
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_projects_discovery_with_include(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'discovery': {
                'include': [
                    '^project.*',
                ],
            },
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1', 'project2', 'tmp_project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_has_calls(
        [
            mock.call(
                'project1',
                [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values],
            ),
            mock.call(
                'project2',
                [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values],
            ),
        ]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}',
            value=value,
            tags=[
                'endpoint:http://localhost:9000',
                'component:project1',
            ],
        )
        aggregator.assert_metric(
            f'sonarqube.{metric}',
            value=value,
            tags=[
                'endpoint:http://localhost:9000',
                'component:project2',
            ],
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_projects_discovery_with_include_and_exclude(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'discovery': {
                'include': [
                    '^project1.*',
                ],
                'exclude': [
                    '^tmp_.*',
                ],
            },
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1', 'project2', 'tmp_project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_has_calls(
        [
            mock.call(
                'project1',
                [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values],
            ),
        ]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}',
            value=value,
            tags=[
                'endpoint:http://localhost:9000',
                'component:project1',
            ],
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )


@mock.patch("datadog_checks.sonarqube.check.Api")
def test_projects_keys_and_discovery_with_exclude(mock_api, aggregator, dd_run_check, sonarqube_check):
    # Given
    config = {
        'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
        'projects': {
            'keys': [
                'project1',
            ],
            'discovery': {
                'exclude': [
                    '^tmp_.*',
                ],
            },
        },
    }
    mock_api.return_value.get_projects.return_value = ['project1', 'project2', 'tmp_project1']
    mock_api.return_value.get_metrics.return_value = [metric for metric in METRICS]
    excluded_metrics = [metric for metric in METRICS if re.search('^.*\\.new_.*', metric)]
    included_metrics = [metric for metric in METRICS if metric not in excluded_metrics]
    metrics_with_values = [(metric, randrange(0, 100)) for metric in included_metrics]
    measures = [(f"{metric.split('.')[1]}", value) for metric, value in metrics_with_values]
    mock_api.return_value.get_measures.return_value = measures
    check = sonarqube_check(config)
    # When
    dd_run_check(check)
    # Then
    mock_api.return_value.get_measures.assert_has_calls(
        [
            mock.call(
                'project1',
                [f"{metric.split('.')[1]}" for metric, _ in metrics_with_values],
            ),
        ]
    )
    for metric, value in metrics_with_values:
        aggregator.assert_metric(
            f'sonarqube.{metric}',
            value=value,
            tags=[
                'endpoint:http://localhost:9000',
                'component:project1',
            ],
        )
    aggregator.assert_service_check(
        'sonarqube.api_access',
        status=check.OK,
        tags=['endpoint:http://localhost:9000'],
    )
