# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy

import mock
import pytest
import requests

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab_runner import GitlabRunnerCheck

from . import common


def build_minimal_check():
    return GitlabRunnerCheck(
        'gitlab_runner',
        {'allowed_metrics': ['ci_runner_errors']},
        instances=[{'prometheus_endpoint': 'http://host/metrics'}],
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    'test_case, timeout_config, expected_timeout',
    [
        ("legacy config", {"connect_timeout": 8, "receive_timeout": 7}, (8, 7)),
        ("new config", {"connect_timeout": 8, "read_timeout": 7}, (8, 7)),
        ("default timeout", {}, (5, 15)),
    ],
)
def test_timeout(test_case, timeout_config, expected_timeout):
    config = deepcopy(common.CONFIG)

    config['instances'][0].update(timeout_config)

    gitlab_runner = GitlabRunnerCheck('gitlab_runner', common.CONFIG['init_config'], instances=config['instances'])

    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200)

        gitlab_runner.check(config['instances'][0])

        r.get.assert_called_with(
            'http://localhost:8085/ci',
            auth=mock.ANY,
            cert=mock.ANY,
            headers=mock.ANY,
            proxies=mock.ANY,
            timeout=expected_timeout,
            verify=mock.ANY,
            allow_redirects=mock.ANY,
        )


@pytest.mark.unit
def test_job_queue_duration_metric(aggregator, dd_run_check, mock_data):
    """
    Test that the gitlab_runner_job_queue_duration_seconds histogram metric
    is automatically collected via METRICS_LIST without user configuration.
    """
    config = deepcopy(common.CONFIG)

    check = GitlabRunnerCheck('gitlab_runner', config['init_config'], instances=config['instances'])
    dd_run_check(check)
    dd_run_check(check)

    expected_tags = ['runner:test-runner'] + common.CUSTOM_TAGS

    # Histogram buckets (reported as .count with upper_bound tags)
    aggregator.assert_metric(
        'gitlab_runner.gitlab_runner_job_queue_duration_seconds.count',
        tags=expected_tags + ['upper_bound:none'],
    )
    # Histogram sum
    aggregator.assert_metric('gitlab_runner.gitlab_runner_job_queue_duration_seconds.sum', tags=expected_tags)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at gitlab_runner.py:27 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert GitlabRunnerCheck.DEFAULT_METRIC_LIMIT == 0


@pytest.mark.unit
def test_init_uses_first_instance_only():
    # Kills the core/NumberReplacer mutant at gitlab_runner.py:40 (instances[0] -> instances[-1]).
    instances = [
        {'prometheus_endpoint': 'http://first/metrics'},
        {'prometheus_endpoint': 'http://second/metrics'},
    ]
    check = GitlabRunnerCheck('gitlab_runner', {'allowed_metrics': ['ci_runner_errors']}, instances=instances)

    assert list(check.config_map.keys()) == ['http://first/metrics']


@pytest.mark.unit
def test_connection_error_is_caught_and_reported_as_critical(aggregator):
    # Kills the core/ExceptionReplacer mutant at gitlab_runner.py:55 (ConnectionError class name mangled).
    config = deepcopy(common.CONFIG)
    check = GitlabRunnerCheck('gitlab_runner', config['init_config'], instances=config['instances'])

    with mock.patch.object(check, 'process', side_effect=requests.exceptions.ConnectionError('boom')):
        with mock.patch.object(type(check.http), 'get', return_value=mock.MagicMock(status_code=200)):
            check.check(config['instances'][0])

    aggregator.assert_service_check(
        GitlabRunnerCheck.PROMETHEUS_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.CRITICAL,
        tags=common.CUSTOM_TAGS,
        message='Unable to retrieve Prometheus metrics',
    )


@pytest.mark.unit
def test_ci_runner_version_info_removed_from_allowed_metrics():
    # Kills the core/AddNot mutant at gitlab_runner.py:81 ('in' -> 'not in').
    check = build_minimal_check()
    init_config = {'allowed_metrics': ['ci_runner_version_info', 'ci_runner_errors']}
    instance = {'prometheus_endpoint': 'http://host/metrics'}

    result = check._create_gitlab_runner_prometheus_instance(instance, init_config)

    assert 'ci_runner_version_info' not in result['metrics']
    assert 'ci_runner_errors' in result['metrics']


@pytest.mark.unit
def test_send_monotonic_counter_defaults_to_false():
    # Kills the core/ReplaceFalseWithTrue mutant at gitlab_runner.py:97 (send_monotonic_counter default False -> True).
    check = build_minimal_check()
    instance = {'prometheus_endpoint': 'http://host/metrics'}
    init_config = {'allowed_metrics': ['ci_runner_errors']}

    result = check._create_gitlab_runner_prometheus_instance(instance, init_config)

    assert result['send_monotonic_counter'] is False


@pytest.mark.unit
def test_health_service_check_defaults_to_false():
    # Kills the core/ReplaceFalseWithTrue mutant at gitlab_runner.py:98 (health_service_check default False -> True).
    check = build_minimal_check()
    instance = {'prometheus_endpoint': 'http://host/metrics'}
    init_config = {'allowed_metrics': ['ci_runner_errors']}

    result = check._create_gitlab_runner_prometheus_instance(instance, init_config)

    assert result['health_service_check'] is False


@pytest.mark.unit
def test_master_check_uses_port_443_for_https(aggregator):
    # Kills the core comparison/number mutants at gitlab_runner.py:120 that break the https->443 branch.
    check = build_minimal_check()

    with mock.patch.object(type(check.http), 'get', return_value=mock.MagicMock(status_code=200)):
        check._check_connectivity_to_master({'gitlab_url': 'https://example.com/ci'}, [])

    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.OK,
        tags=['gitlab_host:example.com', 'gitlab_port:443'],
    )


@pytest.mark.unit
def test_master_check_defaults_to_port_80_for_non_https_without_port(aggregator):
    # Kills the core comparison/number/logic mutants at gitlab_runner.py:120 that break the default port-80 fallback.
    check = build_minimal_check()

    with mock.patch.object(type(check.http), 'get', return_value=mock.MagicMock(status_code=200)):
        check._check_connectivity_to_master({'gitlab_url': 'http://example.com/ci'}, [])

    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.OK,
        tags=['gitlab_host:example.com', 'gitlab_port:80'],
    )


@pytest.mark.unit
def test_master_check_uses_explicit_port_for_non_https(aggregator):
    # Kills the core/ReplaceOrWithAnd mutant at gitlab_runner.py:120 (port or 80 -> port and 80) for explicit ports.
    check = build_minimal_check()

    with mock.patch.object(type(check.http), 'get', return_value=mock.MagicMock(status_code=200)):
        check._check_connectivity_to_master({'gitlab_url': 'http://example.com:8080/ci'}, [])

    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.OK,
        tags=['gitlab_host:example.com', 'gitlab_port:8080'],
    )


@pytest.mark.unit
def test_master_check_scheme_greater_than_https_still_defaults_to_80(aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at gitlab_runner.py:120 (scheme >= 'https').
    check = build_minimal_check()

    with mock.patch.object(type(check.http), 'get', return_value=mock.MagicMock(status_code=200)):
        check._check_connectivity_to_master({'gitlab_url': 'zzz://example.com/ci'}, [])

    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.OK,
        tags=['gitlab_host:example.com', 'gitlab_port:80'],
    )


@pytest.mark.unit
def test_master_check_status_code_below_200_triggers_critical(aggregator):
    # Kills the core/ReplaceComparisonOperator_NotEq_Gt mutant at gitlab_runner.py:127 (status_code != 200 -> > 200).
    check = build_minimal_check()

    with mock.patch.object(type(check.http), 'get', return_value=mock.MagicMock(status_code=199)):
        with pytest.raises(Exception, match='Http status code 199'):
            check._check_connectivity_to_master({'gitlab_url': 'http://example.com/ci'}, [])

    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.CRITICAL,
        tags=['gitlab_host:example.com', 'gitlab_port:80'],
    )


@pytest.mark.unit
def test_master_check_status_code_above_200_triggers_critical(aggregator):
    # Kills the core/ReplaceComparisonOperator_NotEq_Lt mutant at gitlab_runner.py:127 (status_code != 200 -> < 200).
    check = build_minimal_check()

    with mock.patch.object(type(check.http), 'get', return_value=mock.MagicMock(status_code=201)):
        with pytest.raises(Exception, match='Http status code 201'):
            check._check_connectivity_to_master({'gitlab_url': 'http://example.com/ci'}, [])

    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.CRITICAL,
        tags=['gitlab_host:example.com', 'gitlab_port:80'],
    )


@pytest.mark.unit
def test_master_check_timeout_sets_critical_and_reraises(aggregator):
    # Kills the core/ExceptionReplacer mutant at gitlab_runner.py:138 (requests.exceptions.Timeout -> bogus class).
    check = build_minimal_check()

    with mock.patch.object(type(check.http), 'get', side_effect=requests.exceptions.Timeout()):
        with pytest.raises(requests.exceptions.Timeout):
            check._check_connectivity_to_master({'gitlab_url': 'http://example.com/ci'}, [])

    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.CRITICAL,
        tags=['gitlab_host:example.com', 'gitlab_port:80'],
        message='Timeout when hitting',
    )


@pytest.mark.unit
def test_master_check_generic_error_sets_critical_and_reraises(aggregator):
    # Kills the core/ExceptionReplacer mutant at gitlab_runner.py:147 (except Exception -> bogus class).
    check = build_minimal_check()

    with mock.patch.object(type(check.http), 'get', side_effect=ValueError('boom')):
        with pytest.raises(ValueError, match='boom'):
            check._check_connectivity_to_master({'gitlab_url': 'http://example.com/ci'}, [])

    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.CRITICAL,
        tags=['gitlab_host:example.com', 'gitlab_port:80'],
        message='Error hitting',
    )
