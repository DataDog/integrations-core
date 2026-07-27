# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.http import assert_http_capability


def assert_http_client_config(http, expected_http_kwargs):
    for key, value in expected_http_kwargs.items():
        assert_http_capability(http, key, value)


def assert_request_timeout(check_or_http, expected):
    http = getattr(check_or_http, 'http', check_or_http)
    timeout = http.default_timeout
    assert (timeout.connect, timeout.read) == expected
