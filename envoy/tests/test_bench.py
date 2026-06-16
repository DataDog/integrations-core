# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.envoy import Envoy

from .common import DEFAULT_INSTANCE, get_fixture_path


def test_openmetrics_check(benchmark, mock_http_response):
    mock_http_response(file_path=get_fixture_path('./openmetrics/openmetrics.txt'))

    c = Envoy('envoy', {}, [DEFAULT_INSTANCE])

    # Run once to get any first-run overhead out of the way.
    c.check(DEFAULT_INSTANCE)

    benchmark(c.check, DEFAULT_INSTANCE)
