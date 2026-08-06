# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.kube_proxy import KubeProxyCheck

pytestmark = pytest.mark.unit

CHECK_NAME = 'kube_proxy'
instance = {'prometheus_url': 'http://localhost:10249/metrics'}
instance2 = {'prometheus_url': 'http://localhost:10249/metrics', 'health_url': 'http://1.2.3.4:5678/healthz'}


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at kube_proxy.py:36 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KubeProxyCheck.DEFAULT_METRIC_LIMIT == 0


def test_send_histograms_buckets_enabled_by_default():
    # Kills the core/ReplaceTrueWithFalse mutant at kube_proxy.py:62 (send_histograms_buckets True -> False).
    check = KubeProxyCheck(CHECK_NAME, {}, [instance])
    scraper_config = check.get_scraper_config(instance)
    assert scraper_config['send_histograms_buckets'] is True


def test_healthcheck_config_defaults_when_ca_cert_present(monkeypatch):
    captured = {}

    def fake_requests_wrapper(config, init_config, remapper, log):
        captured.update(config)

    monkeypatch.setattr('datadog_checks.kube_proxy.kube_proxy.RequestsWrapper', fake_requests_wrapper)
    check = KubeProxyCheck(CHECK_NAME, {}, [instance])

    check._healthcheck_http_handler({'ssl_ca_cert': '/path/to/ca.pem'}, 'http://1.2.3.4:5678/healthz')

    # Kills the core/ReplaceTrueWithFalse mutant at kube_proxy.py:98 (ssl_verify default True -> False).
    assert captured['tls_verify'] is True
    # Kills the core/ReplaceFalseWithTrue mutant at kube_proxy.py:99 (ssl_ignore_warning default False -> True).
    assert captured['tls_ignore_warning'] is False


def test_healthcheck_config_overrides_when_ca_cert_missing(monkeypatch):
    captured = {}

    def fake_requests_wrapper(config, init_config, remapper, log):
        captured.update(config)

    monkeypatch.setattr('datadog_checks.kube_proxy.kube_proxy.RequestsWrapper', fake_requests_wrapper)
    check = KubeProxyCheck(CHECK_NAME, {}, [instance])

    check._healthcheck_http_handler({}, 'http://1.2.3.4:5678/healthz')

    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at kube_proxy.py:102
    # (tls_ca_cert is None check) and the core/ReplaceTrueWithFalse mutant at kube_proxy.py:103.
    assert captured['tls_ignore_warning'] is True
    # Kills the core/ReplaceFalseWithTrue mutant at kube_proxy.py:104 (tls_verify override True -> False).
    assert captured['tls_verify'] is False


def test_init_resolves_health_url_for_every_instance_in_the_list():
    first = {'prometheus_url': 'http://localhost:10249/metrics'}
    second = {'prometheus_url': 'http://otherhost:9999/metrics'}

    check = KubeProxyCheck(CHECK_NAME, {}, [first, second])

    # Kills the core/ReplaceComparisonOperator_IsNot_Is and core/AddNot mutants at kube_proxy.py:39
    # (instances is not None check) and the core/ZeroIterationForLoop mutant at kube_proxy.py:40,
    # all of which would leave 'health_url' unresolved on some or all instances.
    assert check.instances[0]['health_url'] == 'http://localhost:10256/healthz'
    assert check.instances[1]['health_url'] == 'http://otherhost:10256/healthz'


def test_init_preserves_explicit_health_url():
    instance_with_health_url = {
        'prometheus_url': 'http://localhost:10249/metrics',
        'health_url': 'http://custom:1234/healthz',
    }

    check = KubeProxyCheck(CHECK_NAME, {}, [instance_with_health_url])

    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at kube_proxy.py:46
    # (url is None check), which would overwrite an explicitly configured health_url.
    assert check.instance['health_url'] == 'http://custom:1234/healthz'


def test_init_leaves_health_url_none_when_prometheus_url_has_no_port():
    instance_without_port = {'prometheus_url': 'http://localhost/metrics'}

    check = KubeProxyCheck(CHECK_NAME, {}, [instance_without_port])

    # Kills the core/ReplaceAndWithOr mutant at kube_proxy.py:46, which would attempt the
    # health_url substitution even when the port regex does not match.
    assert check.instance['health_url'] is None


def test_perform_service_check_skips_when_health_url_missing():
    check = KubeProxyCheck(CHECK_NAME, {}, [{'prometheus_url': 'http://localhost/metrics'}])
    mock_service_check = mock.Mock()
    check.service_check = mock_service_check

    check._perform_service_check(check.instance)

    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at kube_proxy.py:76
    # (url is None check), which would run the health check even without a health_url.
    mock_service_check.assert_not_called()


def test_perform_service_check_reports_critical_on_request_exception(monkeypatch):
    check = KubeProxyCheck(CHECK_NAME, {}, [instance2])
    mock_service_check = mock.Mock()
    monkeypatch.setattr(check, 'service_check', mock_service_check)

    raise_error = mock.Mock(side_effect=requests.HTTPError('health check failed'))
    with mock.patch('requests.Session.get', return_value=mock.MagicMock(raise_for_status=raise_error)):
        check._perform_service_check(check.instance)

    # Kills the core/ExceptionReplacer mutant at kube_proxy.py:87, which replaces the caught
    # exception type so a real RequestException would propagate uncaught instead of being reported.
    mock_service_check.assert_called_once_with(
        'kubeproxy.up', AgentCheck.CRITICAL, tags=[], message='health check failed'
    )
