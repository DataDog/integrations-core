# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.kube_leader import ElectionRecordAnnotation
from datadog_checks.kube_controller_manager import KubeControllerManagerCheck

pytestmark = pytest.mark.unit

# Constants
CHECK_NAME = 'kube_controller_manager'
NAMESPACE = 'kube_controller_manager'

instance = {
    'prometheus_url': 'http://localhost:10252/metrics',
    'extra_queues': ['extra'],
    'extra_limiters': ['extra_controller'],
    'ignore_deprecated': False,
}

instance2 = {
    'prometheus_url': 'http://localhost:10252/metrics',
    'extra_queues': ['extra'],
    'extra_limiters': ['extra_controller'],
    'ignore_deprecated': True,
}


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.Session.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


@pytest.fixture()
def mock_leader():
    # Inject a fake object in the leader-election monitoring logic
    with mock.patch(
        'datadog_checks.kube_controller_manager.KubeControllerManagerCheck._get_record',
        return_value=ElectionRecordAnnotation(
            "endpoints",
            '{"holderIdentity":"pod1","leaseDurationSeconds":15,"leaderTransitions":3,'
            + '"acquireTime":"2018-12-19T18:23:24Z","renewTime":"2019-01-02T16:30:07Z"}',
        ),
    ):
        yield


@pytest.fixture()
def check():
    # A minimally-configured check instance for tests that exercise helpers directly, not the full check() pipeline.
    return KubeControllerManagerCheck(
        CHECK_NAME, {}, [{'prometheus_url': 'http://localhost:10252/metrics', 'slis_available': False}]
    )


# This is the same end-to-end metrics assertion used in test_kube_controller_manager.py. It is ported here
# because cosmic-ray mutation runs for this integration execute tests/test_unit.py in isolation, so the broad
# coverage it gives kube_controller_manager.py needs to live in this file too.
def test_check_metrics_with_deprecated(aggregator, mock_metrics, mock_leader):
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    generic_check_metrics(aggregator, True)


def test_check_metrics_without_deprecated(aggregator, mock_metrics, mock_leader):
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance2)

    generic_check_metrics(aggregator, False)


def generic_check_metrics(aggregator, check_deprecated):
    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.goroutines')
    assert_metric('.threads')
    assert_metric('.open_fds')
    assert_metric('.client.http.requests')
    assert_metric('.max_fds')

    assert_metric('.nodes.evictions', metric_type=aggregator.MONOTONIC_COUNT, value=1, tags=["zone:test"])
    assert_metric('.nodes.evictions', metric_type=aggregator.MONOTONIC_COUNT, value=3, tags=["zone:test-total"])
    assert_metric('.nodes.count', value=5, tags=["zone:test"])
    assert_metric('.nodes.unhealthy', value=1, tags=["zone:test"])

    assert_metric('.rate_limiter.use', value=1, tags=["limiter:job_controller"])
    assert_metric('.rate_limiter.use', value=0, tags=["limiter:daemon_controller"])

    assert_metric('.queue.adds', metric_type=aggregator.MONOTONIC_COUNT, value=238.0, tags=["queue:replicaset"])
    assert_metric('.queue.depth', metric_type=aggregator.GAUGE, value=29, tags=["queue:service"])
    assert_metric('.queue.retries', metric_type=aggregator.MONOTONIC_COUNT, value=1283, tags=["queue:deployment"])

    if check_deprecated:
        assert_metric('.queue.work_duration.sum', value=2124279, tags=["queue:replicaset"])
        assert_metric('.queue.work_duration.count', value=238, tags=["queue:replicaset"])
        assert_metric('.queue.work_duration.quantile', value=144, tags=["queue:replicaset", "quantile:0.5"])

        assert_metric('.queue.latency.sum', value=1953629, tags=["queue:deployment"])
        assert_metric('.queue.latency.count', value=1454, tags=["queue:deployment"])
        assert_metric('.queue.latency.quantile', value=15195, tags=["queue:deployment", "quantile:0.9"])

    # Extra name from the instance
    assert_metric('.rate_limiter.use', value=0, tags=["limiter:extra_controller"])
    assert_metric('.queue.adds', metric_type=aggregator.MONOTONIC_COUNT, value=99.0, tags=["queue:daemonset"])
    assert_metric('.queue.depth', metric_type=aggregator.GAUGE, value=0, tags=["queue:daemonset"])
    assert_metric('.queue.retries', metric_type=aggregator.MONOTONIC_COUNT, value=4, tags=["queue:daemonset"])

    # Metrics from 1.14
    assert_metric('.queue.work_longest_duration', value=2, tags=["queue:daemonset"])
    assert_metric('.queue.work_unfinished_duration', value=1, tags=["queue:daemonset"])
    assert_metric('.queue.process_duration.count', value=51.0, tags=["queue:daemonset", "upper_bound:0.001"])
    assert_metric('.queue.process_duration.sum', value=0.7717836519999999, tags=["queue:daemonset"])
    assert_metric('.queue.queue_duration.count', value=99.0, tags=["queue:daemonset", "upper_bound:none"])
    assert_metric('.queue.queue_duration.sum', value=0.3633380879999999, tags=["queue:daemonset"])

    # Metrics from 1.26
    assert_metric('.job_controller.terminated_pods_tracking_finalizer', value=6, tags=["event:add"])
    assert_metric('.job_controller.terminated_pods_tracking_finalizer', value=6, tags=["event:delete"])

    # Leader election mixin
    expected_le_tags = ["record_kind:endpoints", "record_name:kube-controller-manager", "record_namespace:kube-system"]
    assert_metric('.leader_election.transitions', value=3, tags=expected_le_tags)
    assert_metric('.leader_election.lease_duration', value=15, tags=expected_le_tags)
    aggregator.assert_service_check(NAMESPACE + ".leader_election.status", tags=expected_le_tags)

    aggregator.assert_all_metrics_covered()


def test_service_check_ok(monkeypatch):
    instance = {'prometheus_url': 'http://localhost:10252/metrics'}
    instance_tags = []

    check = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])

    monkeypatch.setattr(check, 'service_check', mock.Mock())

    calls = [
        mock.call('kube_controller_manager.up', AgentCheck.OK, tags=instance_tags),
        mock.call('kube_controller_manager.up', AgentCheck.CRITICAL, tags=instance_tags, message='health check failed'),
    ]

    # successful health check
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(status_code=200)):
        check._perform_service_check(instance)

    # failed health check
    raise_error = mock.Mock()
    raise_error.side_effect = requests.HTTPError('health check failed')
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(raise_for_status=raise_error)):
        check._perform_service_check(instance)

    check.service_check.assert_has_calls(calls)


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at kube_controller_manager.py:24 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KubeControllerManagerCheck.DEFAULT_METRIC_LIMIT == 0


def test_default_ignore_deprecated_is_false():
    # Kills the core/ReplaceFalseWithTrue mutant at kube_controller_manager.py:25 (DEFAULT_IGNORE_DEPRECATED->True).
    assert KubeControllerManagerCheck.DEFAULT_IGNORE_DEPRECATED is False


def test_health_url_not_overwritten_when_already_set():
    # Kills the core/ReplaceAndWithOr mutant at kube_controller_manager.py:147 (`and` -> `or`).
    instance = {
        'prometheus_url': 'http://localhost:10252/metrics',
        'health_url': 'http://custom/healthz',
        'slis_available': False,
    }
    KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    assert instance['health_url'] == 'http://custom/healthz'


def test_slis_available_not_overridden_when_preset():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at kube_controller_manager.py:154.
    instance = {'prometheus_url': 'http://localhost:10252/metrics', 'slis_available': False}
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(status_code=200)):
        KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    assert instance['slis_available'] is False


def test_slis_available_detected_when_not_preset():
    # Covers the non-mutated happy path of kube_controller_manager.py:154, complementing the preset-value test above.
    instance = {'prometheus_url': 'http://localhost:10252/metrics'}
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(status_code=200)):
        KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    assert instance['slis_available'] is True


def test_sli_metrics_skipped_when_not_available(monkeypatch):
    # Kills the core/ReplaceAndWithOr mutant at kube_controller_manager.py:192 (`and` -> `or`).
    instance = {
        'prometheus_url': 'http://localhost:10252/metrics',
        'slis_available': False,
        'leader_election': False,
    }
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    processed_configs = []
    monkeypatch.setattr(c, 'process', lambda config, metric_transformers=None: processed_configs.append(config))
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(status_code=200)):
        c.check(instance)
    assert len(processed_configs) == 1


def test_sli_metrics_processed_when_available(monkeypatch):
    # Kills the core/AddNot mutant at kube_controller_manager.py:192 (negates the `sli_scraper_config` operand).
    instance = {
        'prometheus_url': 'http://localhost:10252/metrics',
        'slis_available': True,
        'leader_election': False,
    }
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    processed_configs = []
    monkeypatch.setattr(c, 'process', lambda config, metric_transformers=None: processed_configs.append(config))
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(status_code=200)):
        c.check(instance)
    assert len(processed_configs) == 2


def test_healthcheck_config_ssl_verify_defaults_true(check):
    # Kills the core/ReplaceTrueWithFalse mutant at kube_controller_manager.py:267 (ssl_verify default True -> False).
    handler = check._healthcheck_http_handler({'ssl_ca_cert': '/tmp/ca.pem'}, 'http://localhost:10252/healthz')
    assert handler.tls_config['tls_verify'] is True


def test_healthcheck_config_ssl_ignore_warning_defaults_false(check):
    # Kills the ReplaceFalseWithTrue mutant at kube_controller_manager.py:268 (ssl_ignore_warning default False->True).
    handler = check._healthcheck_http_handler({'ssl_ca_cert': '/tmp/ca.pem'}, 'http://localhost:10252/healthz')
    assert handler.tls_config['tls_ignore_warning'] is False


def test_healthcheck_config_not_overridden_when_ca_cert_set(check):
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at kube_controller_manager.py:271.
    handler = check._healthcheck_http_handler(
        {'ssl_ca_cert': '/tmp/ca.pem', 'ssl_verify': True, 'ssl_ignore_warning': False},
        'http://localhost:10252/healthz',
    )
    assert handler.tls_config['tls_verify'] is True
    assert handler.tls_config['tls_ignore_warning'] is False


def test_healthcheck_config_overridden_when_no_ca_cert(check):
    # Kills the ReplaceTrueWithFalse mutant at line 272 and the ReplaceFalseWithTrue mutant at line 273.
    handler = check._healthcheck_http_handler(
        {'ssl_verify': True, 'ssl_ignore_warning': False}, 'http://localhost:10252/healthz'
    )
    assert handler.tls_config['tls_ignore_warning'] is True
    assert handler.tls_config['tls_verify'] is False


def test_detect_sli_endpoint_requests_with_streaming(check):
    # Kills the core/ReplaceTrueWithFalse mutant at sli_metrics.py:53 (`stream=True` -> `stream=False`).
    http_handler = mock.Mock()
    http_handler.get.return_value = mock.MagicMock(status_code=200)
    check.detect_sli_endpoint(http_handler, 'http://localhost:10257/metrics/slis')
    http_handler.get.assert_called_once_with('http://localhost:10257/metrics/slis', stream=True)


def test_detect_sli_endpoint_returns_false_on_request_exception(check):
    # Kills the core/ReplaceFalseWithTrue mutant at sli_metrics.py:56 (`return False` -> `return True` on error).
    http_handler = mock.Mock()
    http_handler.get.side_effect = Exception('boom')
    assert check.detect_sli_endpoint(http_handler, 'http://localhost:10257/metrics/slis') is False


def test_detect_sli_endpoint_logs_permission_hint_only_at_403(check, monkeypatch):
    # Kills the core/ReplaceComparisonOperator_Eq_* and core/AddNot/NumberReplacer mutants at sli_metrics.py:57.
    monkeypatch.setattr(check, 'log', mock.Mock())
    http_handler = mock.Mock()
    for status_code, should_log in [(403, True), (402, False), (404, False)]:
        check.log.reset_mock()
        http_handler.get.return_value = mock.MagicMock(status_code=status_code)
        check.detect_sli_endpoint(http_handler, 'http://localhost:10257/metrics/slis')
        assert check.log.debug.called is should_log


def test_detect_sli_endpoint_returns_true_only_for_200(check):
    # Kills the core/ReplaceComparisonOperator_Eq_* and core/NumberReplacer mutants at sli_metrics.py:62.
    http_handler = mock.Mock()
    for status_code, expected in [(200, True), (199, False), (201, False)]:
        http_handler.get.return_value = mock.MagicMock(status_code=status_code)
        assert check.detect_sli_endpoint(http_handler, 'http://localhost:10257/metrics/slis') is expected


class FakeMetric:
    def __init__(self, name, samples):
        self.name = name
        self.samples = samples


def test_sli_metrics_transformer_keeps_only_healthz_type_samples(check):
    # Kills the ZeroIterationForLoop mutant at sli_metrics.py:68 and the ReplaceComparisonOperator_Eq_*/AddNot
    # mutants at sli_metrics.py:70 (`metric_type == "healthz"`). The matching sample's type is built via json.loads
    # rather than a literal so it isn't interned to the same object as the source's "healthz" literal, which also
    # kills the Eq_Is mutant (`is` would wrongly compare identity instead of value here).
    metric = FakeMetric(
        name='kubernetes_healthcheck',
        samples=[
            [None, {'type': 'cronjob', 'name': 'a'}, 1],
            [None, {'type': json.loads('"healthz"'), 'name': 'b'}, 1],
            [None, {'type': 'readyz', 'name': 'c'}, 1],
        ],
    )
    submitted = {}
    check.submit_openmetric = lambda metric_name, modified_metric, scraper_config: submitted.update(
        metric=modified_metric
    )
    check.sli_metrics_transformer(metric, {})
    kept_names = [sample[1]['sli_name'] for sample in submitted['metric'].samples]
    assert kept_names == ['b']
