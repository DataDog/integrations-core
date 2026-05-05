# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import Mock

from datadog_checks.base.utils.discovery.verifiers import (
    body_contains,
    body_matches,
    is_prometheus_exposition,
    json_has,
    response_equals,
    response_starts_with,
    status_2xx,
)


def _resp(status=200, content_type="text/plain", body="", json_body=None):
    r = Mock()
    r.status_code = status
    r.headers = {"Content-Type": content_type}
    r.text = body
    if json_body is not None:
        r.json = Mock(return_value=json_body)
    else:
        r.json = Mock(side_effect=ValueError("not json"))
    return r


def test_status_2xx_pass():
    assert status_2xx()(_resp(status=200))
    assert status_2xx()(_resp(status=204))


def test_status_2xx_fail():
    assert not status_2xx()(_resp(status=301))
    assert not status_2xx()(_resp(status=500))


def test_body_contains_pass():
    assert body_contains("Total Accesses:")(_resp(body="Total Accesses: 42\n"))


def test_body_contains_fail_on_substring_absent():
    assert not body_contains("Total Accesses:")(_resp(body="something else"))


def test_body_contains_fail_on_non_2xx():
    assert not body_contains("anything")(_resp(status=500, body="anything"))


def test_body_matches_pass():
    assert body_matches(r"^Active connections:")(_resp(body="Active connections: 7\nblah"))


def test_body_matches_anchored_to_start_of_a_line_using_multiline_flag():
    # Demonstrates the convention: callers pass plain re patterns; we apply re.MULTILINE.
    assert body_matches(r"^server: nginx$")(_resp(body="HTTP/1.1 200 OK\nserver: nginx\n"))


def test_body_matches_fail():
    assert not body_matches(r"^Active connections:")(_resp(body="not nginx"))


def test_json_has_pass_top_level_keys():
    assert json_has(["version", "leader"])(_resp(json_body={"version": "1.7.0", "leader": "h1"}))


def test_json_has_fail_missing_key():
    assert not json_has(["version", "leader"])(_resp(json_body={"version": "1.7.0"}))


def test_json_has_fail_not_json():
    assert not json_has(["x"])(_resp(body="<html/>"))


def test_is_prometheus_exposition_pass_text_plain():
    body = "# HELP foo bar\nfoo 1\n"
    assert is_prometheus_exposition()(_resp(content_type="text/plain; version=0.0.4", body=body))


def test_is_prometheus_exposition_pass_openmetrics():
    body = "foo_total 42\n"
    assert is_prometheus_exposition()(_resp(content_type="application/openmetrics-text", body=body))


def test_is_prometheus_exposition_rejects_html():
    assert not is_prometheus_exposition()(_resp(content_type="text/html", body="<html/>"))


def test_is_prometheus_exposition_rejects_garbage_body():
    body = "this is not prometheus"
    assert not is_prometheus_exposition()(_resp(content_type="text/plain", body=body))


def test_response_equals_tcp_pass():
    assert response_equals(b"imok")(b"imok")


def test_response_equals_tcp_fail():
    assert not response_equals(b"imok")(b"imnotok")


def test_response_starts_with_tcp_pass():
    assert response_starts_with(b"+PONG")(b"+PONG\r\n")


def test_response_starts_with_tcp_fail():
    assert not response_starts_with(b"+PONG")(b"-ERR\r\n")
