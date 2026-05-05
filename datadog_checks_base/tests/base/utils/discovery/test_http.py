# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import Mock, patch

import requests

from datadog_checks.base.utils.discovery.http import http_probe
from datadog_checks.base.utils.discovery.verifiers import body_contains, status_2xx


def _ok_response(body="ok", status=200, content_type="text/plain"):
    r = Mock()
    r.status_code = status
    r.text = body
    r.headers = {"Content-Type": content_type}
    return r


def test_http_probe_uses_correct_url_and_timeout():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response()
        http_probe("10.0.0.1", 9090, "/metrics", verify=status_2xx())
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "http://10.0.0.1:9090/metrics"
        assert kwargs["timeout"] == 0.5


def test_http_probe_passes_when_verify_passes():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response(body="Total Accesses: 42")
        assert http_probe("h", 80, "/server-status?auto", verify=body_contains("Total Accesses:"))


def test_http_probe_fails_when_verify_fails():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response(body="something else")
        assert not http_probe("h", 80, "/x", verify=body_contains("Total Accesses:"))


def test_http_probe_returns_false_on_connection_error():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError()
        assert not http_probe("h", 80, "/x", verify=status_2xx())


def test_http_probe_returns_false_on_timeout():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout()
        assert not http_probe("h", 80, "/x", verify=status_2xx())


def test_http_probe_brackets_ipv6_in_url():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response()
        http_probe("[::1]", 80, "/x", verify=status_2xx())
        args, _ = mock_get.call_args
        assert args[0] == "http://[::1]:80/x"


def test_http_probe_custom_timeout():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response()
        http_probe("h", 80, "/x", verify=status_2xx(), timeout=1.0)
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 1.0
