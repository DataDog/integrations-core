# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.kube_metrics_server import KubeMetricsServerCheck

pytestmark = pytest.mark.unit

CHECK_NAME = 'kube_metrics_server'

BASE_INSTANCE = {'prometheus_url': 'https://localhost:443/metrics'}


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at kube_metrics_server.py:93 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KubeMetricsServerCheck.DEFAULT_METRIC_LIMIT == 0


def test_health_url_computed_from_prometheus_url_when_absent():
    inst = {'prometheus_url': 'https://localhost:443/metrics'}
    KubeMetricsServerCheck(CHECK_NAME, {}, [inst])
    assert inst['health_url'] == 'https://localhost:443/livez'


def test_health_url_untouched_when_already_set():
    # Kills the core/ReplaceAndWithOr mutant at kube_metrics_server.py:101 (and -> or): with an
    # explicit health_url, the "or" mutant would still recompute it from prometheus_url.
    inst = {'health_url': 'https://custom/health', 'prometheus_url': 'https://localhost:443/metrics'}
    KubeMetricsServerCheck(CHECK_NAME, {}, [inst])
    assert inst['health_url'] == 'https://custom/health'


def test_tls_defaults_preserved_when_ca_cert_is_set():
    # Kills the core/ReplaceTrueWithFalse mutant at line:151 (ssl_verify default True -> False) and
    # core/ReplaceFalseWithTrue mutant at line:152 (ssl_ignore_warning default False -> True); also
    # kills the line:155 is/is-not and AddNot mutants, since with a ca_cert set the override must
    # not fire and these defaults must pass through unchanged.
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    handler = check._healthcheck_http_handler({'ssl_ca_cert': '/etc/ssl/ca.pem'}, 'https://localhost/livez')
    assert handler.tls_config['tls_verify'] is True
    assert handler.tls_config['tls_ignore_warning'] is False


def test_tls_overridden_when_ca_cert_is_none():
    # Kills the line:155 is/is-not and AddNot mutants, plus the core/ReplaceTrueWithFalse mutant at
    # line:156 and core/ReplaceFalseWithTrue mutant at line:157: with no ca_cert, the check must
    # force tls_ignore_warning True and tls_verify False.
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    handler = check._healthcheck_http_handler({}, 'https://localhost/livez')
    assert handler.tls_config['tls_verify'] is False
    assert handler.tls_config['tls_ignore_warning'] is True


def test_service_check_skipped_when_health_url_is_none(monkeypatch):
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at line:129
    # (`if url is None: return`): with no health_url, no service check must ever be emitted.
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    monkeypatch.setattr(check, 'service_check', mock.Mock())
    check._perform_service_check({'health_url': None})
    check.service_check.assert_not_called()


def test_service_check_ok_uses_namespaced_check_name(monkeypatch):
    # Kills the core/ReplaceBinaryOperator_Add_* mutants at line:133 (NAMESPACE + '.up'): any
    # operator other than string concatenation either raises or yields a different check name.
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    monkeypatch.setattr(check, 'service_check', mock.Mock())
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(status_code=200)):
        check._perform_service_check({'health_url': 'https://localhost/livez', 'tags': ['custom:tag']})
    check.service_check.assert_called_once_with('kube_metrics_server.up', AgentCheck.OK, tags=['custom:tag'])


def test_service_check_critical_on_request_exception(monkeypatch):
    # Kills the core/ExceptionReplacer mutant at line:140: corrupting the caught exception type
    # would let the HTTPError escape uncaught instead of yielding a CRITICAL service check.
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    monkeypatch.setattr(check, 'service_check', mock.Mock())
    raise_error = mock.Mock(side_effect=requests.HTTPError('health check failed'))
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(raise_for_status=raise_error)):
        check._perform_service_check({'health_url': 'https://localhost/livez', 'tags': []})
    check.service_check.assert_called_once_with(
        'kube_metrics_server.up', AgentCheck.CRITICAL, message='health check failed', tags=[]
    )
