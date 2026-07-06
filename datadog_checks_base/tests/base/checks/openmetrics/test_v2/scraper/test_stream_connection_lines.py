# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from unittest import mock

import pytest

from datadog_checks.base.checks.openmetrics.v2.scraper.base_scraper import OpenMetricsScraper
from datadog_checks.base.utils.http_exceptions import HTTPConnectionError


def _scraper_with_connection_error(exception, *, ignore_connection_errors):
    scraper = OpenMetricsScraper.__new__(OpenMetricsScraper)
    scraper.endpoint = 'http://example.test/metrics'
    scraper.ignore_connection_errors = ignore_connection_errors
    scraper.log = logging.getLogger('test_stream_connection_lines')
    scraper.get_connection = mock.Mock(side_effect=exception)
    return scraper


def test_agnostic_connection_error_swallowed_when_ignored(caplog):
    scraper = _scraper_with_connection_error(HTTPConnectionError('refused'), ignore_connection_errors=True)
    with caplog.at_level(logging.WARNING, logger='test_stream_connection_lines'):
        assert list(scraper.stream_connection_lines()) == []
    assert any(
        'OpenMetrics endpoint http://example.test/metrics is not accessible' in record.message
        for record in caplog.records
    )


def test_agnostic_connection_error_reraised_when_not_ignored():
    scraper = _scraper_with_connection_error(HTTPConnectionError('refused'), ignore_connection_errors=False)
    with pytest.raises(HTTPConnectionError):
        list(scraper.stream_connection_lines())
