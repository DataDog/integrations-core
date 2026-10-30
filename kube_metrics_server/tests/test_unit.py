# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.kube_metrics_server import KubeMetricsServerCheck

pytestmark = pytest.mark.unit

CHECK_NAME = "kube_metrics_server"

BASE_INSTANCE = {"prometheus_url": "https://localhost:443/metrics"}


def test_default_metric_limit_is_zero():
    assert KubeMetricsServerCheck.DEFAULT_METRIC_LIMIT == 0


def test_health_url_computed_from_prometheus_url_when_absent():
    inst = {"prometheus_url": "https://localhost:443/metrics"}
    KubeMetricsServerCheck(CHECK_NAME, {}, [inst])
    assert inst["health_url"] == "https://localhost:443/livez"


def test_health_url_untouched_when_already_set():
    inst = {"health_url": "https://custom/health", "prometheus_url": "https://localhost:443/metrics"}
    KubeMetricsServerCheck(CHECK_NAME, {}, [inst])
    assert inst["health_url"] == "https://custom/health"


def test_tls_defaults_preserved_when_ca_cert_is_set():
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    handler = check._healthcheck_http_handler({"ssl_ca_cert": "/etc/ssl/ca.pem"}, "https://localhost/livez")
    assert handler.tls_config["tls_verify"] is True
    assert handler.tls_config["tls_ignore_warning"] is False


def test_tls_overridden_when_ca_cert_is_none():
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    handler = check._healthcheck_http_handler({}, "https://localhost/livez")
    assert handler.tls_config["tls_verify"] is False
    assert handler.tls_config["tls_ignore_warning"] is True


def test_service_check_skipped_when_health_url_is_none(monkeypatch):
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    monkeypatch.setattr(check, "service_check", mock.Mock())
    check._perform_service_check({"health_url": None})
    check.service_check.assert_not_called()


def test_service_check_ok_uses_namespaced_check_name(monkeypatch):
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    monkeypatch.setattr(check, "service_check", mock.Mock())
    with mock.patch("requests.Session.get", return_value=mock.MagicMock(status_code=200)):
        check._perform_service_check({"health_url": "https://localhost/livez", "tags": ["custom:tag"]})
    check.service_check.assert_called_once_with("kube_metrics_server.up", AgentCheck.OK, tags=["custom:tag"])


def test_service_check_critical_on_request_exception(monkeypatch):
    check = KubeMetricsServerCheck(CHECK_NAME, {}, [dict(BASE_INSTANCE)])
    monkeypatch.setattr(check, "service_check", mock.Mock())
    raise_error = mock.Mock(side_effect=requests.HTTPError("health check failed"))
    with mock.patch("requests.Session.get", return_value=mock.MagicMock(raise_for_status=raise_error)):
        check._perform_service_check({"health_url": "https://localhost/livez", "tags": []})
    check.service_check.assert_called_once_with(
        "kube_metrics_server.up", AgentCheck.CRITICAL, message="health check failed", tags=[]
    )
