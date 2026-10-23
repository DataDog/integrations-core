# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.apache import Apache
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientReadTimeoutError

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('version_in_body', [True, False])
def test_auto_fallback_collects_metrics_and_version(
    aggregator, datadog_agent, fake_http, fake_http_response, version_in_body
):
    endpoint = 'http://apache/server-status'
    fake_http_response(endpoint, '<html>status</html>')
    body = 'Total kBytes: 2\nTotal Accesses: 5\n'
    if version_in_body:
        body += 'ServerVersion: Apache/2.4.62\n'
    fake_http_response(endpoint + '?auto', body, headers={'Server': 'Apache/2.4.62'})
    instance = {'apache_status_url': endpoint, 'disable_generic_tags': True}
    check = Apache('apache', {}, [instance])
    check.check_id = 'apache-http'
    check.check(instance)
    aggregator.assert_metric('apache.net.bytes', value=2048)
    aggregator.assert_metric('apache.net.hits', value=5)
    datadog_agent.assert_metadata('apache-http', {'version.raw': '2.4.62'})
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint), ('GET', endpoint + '?auto')]


@pytest.mark.parametrize('error', [HTTPClientConnectionError, HTTPClientReadTimeoutError])
def test_unavailable_status_reports_critical(aggregator, fake_http, error):
    endpoint = 'http://apache/server-status'
    fake_http.register_response('GET', endpoint, error('unavailable'))
    instance = {'apache_status_url': endpoint, 'disable_generic_tags': True}
    check = Apache('apache', {}, [instance])
    with pytest.raises(error, match='unavailable'):
        check.check(instance)
    aggregator.assert_service_check('apache.can_connect', check.CRITICAL)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]
