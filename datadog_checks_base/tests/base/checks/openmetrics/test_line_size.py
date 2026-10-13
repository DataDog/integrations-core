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
# 64-byte lines read in 16-byte chunks (both options are in KiB). Telemetry reads the body without `iter_lines`.
OPTIONS = {'namespace': 'test', 'metrics': ['m'], 'telemetry': True, 'max_line_size': 0.0625, 'request_size': 0.015625}
V1 = (OpenMetricsBaseCheck, {'prometheus_url': URL, **OPTIONS})
V2 = (OpenMetricsBaseCheckV2, {'openmetrics_endpoint': URL, **OPTIONS})


@pytest.mark.parametrize('check_class, instance', [V1, V2], ids=['v1', 'v2'])
def test_telemetry_does_not_read_long_lines(check_class, instance, dd_run_check):
    response = requests.Response()
    response.status_code = 200
    response.raw = urllib3.HTTPResponse(
        io.BytesIO(gzip.compress(b'x' * 1000)), headers={'Content-Encoding': 'gzip'}, preload_content=False
    )
    with mock.patch('requests.Session.get', return_value=response):
        with pytest.raises(Exception, match='line longer than 64 bytes'):
            dd_run_check(check_class('test', {}, [instance]))
