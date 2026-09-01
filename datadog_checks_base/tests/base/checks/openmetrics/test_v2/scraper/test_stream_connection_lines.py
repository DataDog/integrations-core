# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from unittest import mock

import pytest

from datadog_checks.base.checks.openmetrics.v2.scraper.base_scraper import OpenMetricsScraper
from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientReadTimeoutError,
)

AGNOSTIC_CONNECTION_ERRORS = [
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientReadTimeoutError,
]


def _scraper(*, ignore_connection_errors):
    scraper = OpenMetricsScraper.__new__(OpenMetricsScraper)
    scraper.endpoint = 'http://example.test/metrics'
    scraper.ignore_connection_errors = ignore_connection_errors
    scraper.log = logging.getLogger('test_stream_connection_lines')
    return scraper


@pytest.mark.parametrize('error_cls', AGNOSTIC_CONNECTION_ERRORS)
def test_connection_error_swallowed_when_ignored(caplog, error_cls):
    scraper = _scraper(ignore_connection_errors=True)
    scraper.get_connection = mock.Mock(side_effect=error_cls('refused'))

    with caplog.at_level(logging.WARNING, logger='test_stream_connection_lines'):
        assert list(scraper.stream_connection_lines()) == []

    assert any(
        'OpenMetrics endpoint http://example.test/metrics is not accessible' in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize('error_cls', AGNOSTIC_CONNECTION_ERRORS)
def test_connection_error_reraised_when_not_ignored(error_cls):
    scraper = _scraper(ignore_connection_errors=False)
    scraper.get_connection = mock.Mock(side_effect=error_cls('refused'))

    with pytest.raises(error_cls):
        list(scraper.stream_connection_lines())


def test_mid_stream_read_timeout_swallowed_when_connection_errors_are_ignored() -> None:
    connection = FakeHTTPResponse(
        headers={'Content-Type': 'text/plain'},
        lines=('first',),
        stream_error=HTTPClientReadTimeoutError('slow'),
    )

    scraper = _scraper(ignore_connection_errors=True)
    scraper.get_connection = mock.Mock(return_value=connection)
    stream = scraper.stream_connection_lines()

    assert next(stream) == 'first'
    assert list(stream) == []


def test_mid_stream_read_timeout_reraised_when_connection_errors_are_not_ignored() -> None:
    connection = FakeHTTPResponse(
        headers={'Content-Type': 'text/plain'},
        lines=('first',),
        stream_error=HTTPClientReadTimeoutError('slow'),
    )

    scraper = _scraper(ignore_connection_errors=False)
    scraper.get_connection = mock.Mock(return_value=connection)
    stream = scraper.stream_connection_lines()

    assert next(stream) == 'first'
    with pytest.raises(HTTPClientReadTimeoutError, match='slow'):
        next(stream)
