# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientReadTimeoutError,
    HTTPClientStatusError,
)
from datadog_checks.silk import SilkCheck

pytestmark = pytest.mark.unit


def test_stats_response(fake_http, fake_http_response, instance):
    check = SilkCheck('silk', {}, [instance])
    endpoint = check.url + 'stats/system'
    hits = [{'iops_avg': 42}]
    fake_http_response(endpoint, json_data={'hits': hits})
    assert check._get_data('stats/system') == (hits, 200)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]


def test_error_msg_response(aggregator, instance, fake_http, fake_http_response):
    error_response = {'error_msg': 'Statistics data is unavailable while system is OFFLINE'}
    check = SilkCheck('silk', {}, [instance])
    endpoint = check.url + 'stats/system'
    fake_http_response(endpoint, json_data=error_response)
    assert check._get_data('stats/system') == (None, 200)
    aggregator.assert_service_check(
        'silk.can_connect', SilkCheck.WARNING, message='Received error message: ' + error_response['error_msg']
    )
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]


@pytest.mark.parametrize('error', [HTTPClientConnectionError, HTTPClientReadTimeoutError, HTTPClientStatusError])
def test_system_failure_reports_critical(aggregator, fake_http, instance, error):
    check = SilkCheck('silk', {}, [instance])
    endpoint = check.url + 'system/state'
    fake_http.register_response('GET', endpoint, error('unavailable'))
    with pytest.raises(error, match='unavailable'):
        check.check(instance)
    aggregator.assert_service_check('silk.can_connect', check.CRITICAL)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]
