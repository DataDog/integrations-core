# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from types import SimpleNamespace

import mock
import pytest

from datadog_checks.kube_scheduler import KubeSchedulerCheck
from datadog_checks.kube_scheduler import kube_scheduler as kube_scheduler_module

pytestmark = pytest.mark.unit

CHECK_NAME = 'kube_scheduler'


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at kube_scheduler.py:146 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KubeSchedulerCheck.DEFAULT_METRIC_LIMIT == 0


def test_health_url_untouched_when_explicitly_set(instance):
    # Kills the core/ReplaceAndWithOr mutant at kube_scheduler.py:193 (`and`->`or` overwrites an explicit health_url).
    instance = dict(instance, health_url='http://explicit/healthz')
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    assert instance['health_url'] == 'http://explicit/healthz'


def test_slis_scraper_uses_first_instance_not_last(instance):
    # Kills the core/NumberReplacer mutant at kube_scheduler.py:198 (instances[0] -> instances[-1]).
    first = dict(instance, prometheus_url='http://first:10251/metrics')
    second = dict(instance, prometheus_url='http://second:10251/metrics')
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [first, second])
    assert c.slis_scraper_config['prometheus_url'] == 'http://first:10251/metrics/slis'


def test_check_builds_summary_transformers_from_transform_value_summaries(instance, monkeypatch):
    # Kills the core/ZeroIterationForLoop mutant at kube_scheduler.py:211 (TRANSFORM_VALUE_SUMMARIES.items() -> []).
    monkeypatch.setattr(
        kube_scheduler_module, 'TRANSFORM_VALUE_SUMMARIES', {'fake_summary_microseconds': 'fake.metric'}
    )
    instance = dict(instance, leader_election=False)
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
        with mock.patch.object(c, 'process') as mock_process:
            c.check(instance)
    transformers = mock_process.call_args.kwargs['metric_transformers']
    assert 'fake_summary_microseconds' in transformers


def test_healthcheck_http_handler_defaults_when_ca_cert_present(instance):
    # Kills the core/ReplaceTrueWithFalse and ReplaceFalseWithTrue mutants at kube_scheduler.py:252-253, and the
    # core/ReplaceComparisonOperator_Is_IsNot/AddNot mutants at kube_scheduler.py:256 (a present ca_cert must skip
    # the override branch and keep the ssl_verify/ssl_ignore_warning defaults).
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    handler = c._healthcheck_http_handler({'ssl_ca_cert': True}, 'http://a/healthz')
    assert handler.options['verify'] is True
    assert handler.ignore_tls_warning is False


def test_healthcheck_http_handler_forces_insecure_defaults_when_ca_cert_missing(instance):
    # Kills the core/ReplaceTrueWithFalse and ReplaceFalseWithTrue mutants at kube_scheduler.py:257-258 (a missing
    # ca_cert must force tls_verify=False/tls_ignore_warning=True even when ssl_verify=True was requested).
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    handler = c._healthcheck_http_handler({'ssl_verify': True, 'ssl_ignore_warning': False}, 'http://b/healthz')
    assert handler.options['verify'] is False
    assert handler.ignore_tls_warning is True


def test_detect_sli_endpoint_requests_with_stream_true(instance):
    # Kills the core/ReplaceTrueWithFalse mutant at sli_metrics.py:56 (stream=True -> stream=False).
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c._slis_available = None
    handler = mock.MagicMock()
    handler.get.return_value.status_code = 200
    c.detect_sli_endpoint(handler, 'http://localhost:10251/metrics/slis')
    handler.get.assert_called_once_with('http://localhost:10251/metrics/slis', stream=True)


def test_detect_sli_endpoint_returns_false_on_request_exception(instance):
    # Kills the core/ReplaceFalseWithTrue mutant at sli_metrics.py:59 (the except branch must return False).
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c._slis_available = None
    handler = mock.MagicMock()
    handler.get.side_effect = Exception('boom')
    assert c.detect_sli_endpoint(handler, 'http://localhost:10251/metrics/slis') is False


@pytest.mark.parametrize('status_code,expect_logged', [(403, True), (200, False), (500, False)])
def test_detect_sli_endpoint_logs_permission_hint_only_at_403(instance, status_code, expect_logged):
    # Kills the core/ReplaceComparisonOperator_* and AddNot/NumberReplacer mutants at sli_metrics.py:60
    # (r.status_code == 403 gates a debug log with no effect on the return value).
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c._slis_available = None
    handler = mock.MagicMock()
    handler.get.return_value.status_code = status_code
    with mock.patch.object(c.log, 'debug') as mock_debug:
        c.detect_sli_endpoint(handler, 'http://localhost:10251/metrics/slis')
    assert mock_debug.called is expect_logged


def test_detect_sli_endpoint_available_requires_exact_200(instance):
    # Kills the core/ReplaceComparisonOperator_Eq_LtE mutant at sli_metrics.py:65 (status_code == 200 -> <= 200).
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c._slis_available = None
    handler = mock.MagicMock()
    handler.get.return_value.status_code = 100
    assert c.detect_sli_endpoint(handler, 'http://localhost:10251/metrics/slis') is False


def test_sli_metrics_transformer_filters_by_exact_type_healthz(instance):
    # Kills the core/ReplaceComparisonOperator_Eq_LtE/Eq_GtE/Eq_IsNot mutants at sli_metrics.py:74
    # (metric_type == "healthz" must neither over- nor under-match on string ordering or negation).
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 403
        c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c.submit_openmetric = mock.MagicMock()

    metric = SimpleNamespace(
        name='kubernetes_healthcheck',
        samples=[
            ('kubernetes_healthcheck', {'type': 'healthz', 'name': 'ping'}, 1.0),
            ('kubernetes_healthcheck', {'type': 'aaaa', 'name': 'below'}, 1.0),
            ('kubernetes_healthcheck', {'type': 'zzzz', 'name': 'above'}, 1.0),
        ],
    )

    c.sli_metrics_transformer(metric, scraper_config={})

    submitted_metric = c.submit_openmetric.call_args[0][1]
    assert len(submitted_metric.samples) == 1
    assert submitted_metric.samples[0][1] == {'sli_name': 'ping'}
