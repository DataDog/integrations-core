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
BODY = b'# TYPE metric gauge\nmetric 1\n'
INSTANCE = {'namespace': 'test', 'metrics': ['metric'], 'telemetry': True}


def create_v1_check() -> OpenMetricsBaseCheck:
    return OpenMetricsBaseCheck('openmetrics_test', {}, [{'prometheus_url': ENDPOINT, **INSTANCE}])


def create_v2_check() -> OpenMetricsBaseCheckV2:
    return OpenMetricsBaseCheckV2('openmetrics_test', {}, [{'openmetrics_endpoint': ENDPOINT, **INSTANCE}])


@pytest.mark.parametrize('create_check', [create_v1_check, create_v2_check], ids=['v1', 'v2'])
@pytest.mark.parametrize(
    'headers, payload_size',
    [
        pytest.param({}, len(BODY), id='decoded size without Content-Length'),
        pytest.param({'Content-Length': '12'}, 12, id='Content-Length'),
    ],
)
def test_payload_size(
    create_check: Any, headers: dict[str, str], payload_size: int, dd_run_check: Any, aggregator: Any
):
    response = requests.Response()
    response.status_code = 200
    response.headers.update({'Content-Type': 'text/plain', **headers})
    response.raw = urllib3.HTTPResponse(
        io.BytesIO(gzip.compress(BODY)), headers={'Content-Encoding': 'gzip'}, preload_content=False
    )

    # `response.content` would hold the whole body in memory
    content = mock.PropertyMock(side_effect=AssertionError('the body was read into memory'))
    with (
        mock.patch('requests.Session.get', return_value=response),
        mock.patch.object(requests.Response, 'content', content),
    ):
        dd_run_check(create_check())

    aggregator.assert_metric('test.telemetry.payload.size', value=payload_size)
