# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gzip
import io

import mock
import pytest
import requests
import urllib3

from datadog_checks.base import OpenMetricsBaseCheck, OpenMetricsBaseCheckV2

URL = 'http://example.test/metrics'
# Chunks of 10 bytes (`request_size` is in KiB), smaller than the limit as in production
V1 = (OpenMetricsBaseCheck, {'prometheus_url': URL, 'namespace': 'test', 'metrics': ['m'], 'request_size': 0.01})
V2 = (
    OpenMetricsBaseCheckV2,
    {'openmetrics_endpoint': URL, 'namespace': 'test', 'metrics': ['m'], 'request_size': 0.01},
)


@pytest.mark.parametrize('check_class, instance', [V1, V2], ids=['v1', 'v2'])
@pytest.mark.parametrize('help_size, error', [(50, None), (100, 'line longer than 64 bytes')])
def test_line_size_limit(check_class, instance, help_size, error, dd_run_check, aggregator):
    # The second line is `help_size` + 9 bytes long, the limit is 64 bytes
    body = b'# TYPE m gauge\n# HELP m ' + b'x' * help_size + b'\nm 1\n'
    response = requests.Response()
    response.status_code = 200
    response.raw = urllib3.HTTPResponse(
        io.BytesIO(gzip.compress(body)), headers={'Content-Encoding': 'gzip'}, preload_content=False
    )
    check = check_class('test', {}, [instance])
    with (
        mock.patch('requests.Session.get', return_value=response),
        mock.patch('datadog_checks.base.checks.openmetrics.line_size.MAX_LINE_SIZE', 64),
    ):
        if error:
            with pytest.raises(Exception, match=error):
                dd_run_check(check)
        else:
            dd_run_check(check)
            aggregator.assert_metric('test.m', value=1)
