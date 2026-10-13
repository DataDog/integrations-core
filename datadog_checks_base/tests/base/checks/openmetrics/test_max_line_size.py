# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gzip
import io
from typing import Any
from unittest import mock

import pytest
import requests
import urllib3

from datadog_checks.base import OpenMetricsBaseCheck, OpenMetricsBaseCheckV2

ENDPOINT = 'http://example.test/metrics'
VALID_BODY = b'# TYPE metric gauge\nmetric 1\n'
# 0.05 KiB. Responses are read in chunks of 0.01 KiB (`request_size`), smaller than the limit, as in production.
INSTANCE = {'namespace': 'test', 'metrics': ['metric'], 'max_line_size': 0.05, 'request_size': 0.01}


def create_v1_check() -> OpenMetricsBaseCheck:
    return OpenMetricsBaseCheck('openmetrics_test', {}, [{'prometheus_url': ENDPOINT, **INSTANCE}])


def create_v2_check() -> OpenMetricsBaseCheckV2:
    return OpenMetricsBaseCheckV2('openmetrics_test', {}, [{'openmetrics_endpoint': ENDPOINT, **INSTANCE}])


@pytest.fixture(params=[create_v1_check, create_v2_check], ids=['v1', 'v2'])
def check(request: Any) -> Any:
    return request.param()


def scrape(dd_run_check: Any, check: Any, body: bytes) -> None:
    response = requests.Response()
    response.status_code = 200
    response.headers['Content-Type'] = 'text/plain'
    response.raw = urllib3.HTTPResponse(
        io.BytesIO(gzip.compress(body)), headers={'Content-Encoding': 'gzip'}, preload_content=False
    )
    with mock.patch('requests.Session.get', return_value=response):
        dd_run_check(check)


def test_lines_up_to_the_limit_are_read(check: Any, dd_run_check: Any, aggregator: Any) -> None:
    scrape(dd_run_check, check, VALID_BODY + b'# HELP metric ' + b'x' * 37 + b'\n')

    aggregator.assert_metric('test.metric', value=1)


def test_longer_line_fails_the_check(check: Any, dd_run_check: Any) -> None:
    with pytest.raises(Exception, match='line longer than 51 bytes'):
        scrape(dd_run_check, check, VALID_BODY + b'# HELP metric ' + b'x' * 38 + b'\n')
