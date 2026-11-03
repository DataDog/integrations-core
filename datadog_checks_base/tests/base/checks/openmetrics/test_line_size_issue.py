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
from datadog_checks.base.checks.openmetrics.line_size_issue import ISSUE_NAME, ISSUE_TYPE, _issue_id

ENDPOINT = 'http://example.test/metrics'
VALID_BODY = b'# TYPE metric gauge\nmetric 1\n'
LONG_LINE = b'# HELP metric ' + b'x' * 100 + b'\n'
# 0.05 KiB. Responses are read in chunks of 0.01 KiB (`request_size`), smaller than the limit, as in production.
MAX_LINE_SIZE = 51


def create_v1_check() -> OpenMetricsBaseCheck:
    instance = {
        'prometheus_url': ENDPOINT,
        'namespace': 'test',
        'metrics': ['metric'],
        'max_line_size': 0.05,
        'request_size': 0.01,
    }
    return OpenMetricsBaseCheck('openmetrics_test', {}, [instance])


def create_v2_check() -> OpenMetricsBaseCheckV2:
    instance = {
        'openmetrics_endpoint': ENDPOINT,
        'namespace': 'test',
        'metrics': ['metric'],
        'max_line_size': 0.05,
        'request_size': 0.01,
    }
    return OpenMetricsBaseCheckV2('openmetrics_test', {}, [instance])


def response(body: bytes) -> requests.Response:
    r = requests.Response()
    r.status_code = 200
    r.encoding = 'utf-8'
    r.headers['Content-Type'] = 'text/plain'
    r.raw = urllib3.HTTPResponse(
        io.BytesIO(gzip.compress(body)), headers={'Content-Encoding': 'gzip'}, preload_content=False
    )
    return r


def scrape(dd_run_check: Any, check: Any, body: bytes) -> None:
    with mock.patch('requests.Session.get', return_value=response(body)):
        dd_run_check(check)


@pytest.fixture(params=[create_v1_check, create_v2_check], ids=['v1', 'v2'])
def check(request: Any) -> Any:
    return request.param()


def test_long_line_reports_issue(check: Any, dd_run_check: Any, datadog_agent: Any) -> None:
    with pytest.raises(Exception, match=f'line longer than {MAX_LINE_SIZE} bytes'):
        scrape(dd_run_check, check, VALID_BODY + LONG_LINE)

    issues = datadog_agent._sent_reported_issues['openmetrics_test']
    assert len(issues) == 1
    issue = issues[0]
    assert issue['id'] == _issue_id(check.hostname, 'openmetrics_test', ENDPOINT, 'test')
    assert issue['issue_name'] == ISSUE_NAME
    assert issue['issue_type'] == ISSUE_TYPE
    assert issue['severity'] == check.IssueSeverity['HIGH']
    assert issue['extra'] == {'check_name': 'openmetrics_test', 'endpoint': ENDPOINT, 'max_line_size': MAX_LINE_SIZE}
    assert 'max_line_size' in issue['remediation']['steps'][1]['text']


def test_successful_scrape_resolves_issue(check: Any, dd_run_check: Any, datadog_agent: Any) -> None:
    issue_id = _issue_id(check.hostname, 'openmetrics_test', ENDPOINT, 'test')

    with pytest.raises(Exception, match='line longer than'):
        scrape(dd_run_check, check, LONG_LINE)
    assert issue_id not in datadog_agent._sent_resolved_issues

    scrape(dd_run_check, check, VALID_BODY)
    assert issue_id in datadog_agent._sent_resolved_issues
    assert len(datadog_agent._sent_reported_issues['openmetrics_test']) == 1


def test_reporting_error_does_not_hide_the_check_error(check: Any, dd_run_check: Any) -> None:
    with mock.patch.object(check, 'report_issue', side_effect=RuntimeError('bridge unavailable')):
        with pytest.raises(Exception, match='line longer than'):
            scrape(dd_run_check, check, LONG_LINE)
