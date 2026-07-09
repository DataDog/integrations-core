# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.envoy import Envoy

from .common import DEFAULT_INSTANCE, get_fixture_path

OPENMETRICS_FIXTURE = get_fixture_path('./openmetrics/openmetrics.txt')


def test_openmetrics_check(benchmark, dd_run_check, mock_http_response):
    mock_http_response(file_path=OPENMETRICS_FIXTURE)

    c = Envoy('envoy', {}, [DEFAULT_INSTANCE])
    dd_run_check(c)

    benchmark(c.check, DEFAULT_INSTANCE)
