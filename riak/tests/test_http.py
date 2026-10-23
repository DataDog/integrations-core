# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientReadTimeoutError,
    HTTPClientStatusError,
)
from datadog_checks.riak import Riak

pytestmark = pytest.mark.unit


def test_stats_and_redirect_delta(aggregator, instance, fake_http, fake_http_response):
    endpoint = instance['url']
    fake_http_response(endpoint, json_data={'coord_redirs_total': 10, 'node_gets': 5})
    fake_http_response(endpoint, json_data={'coord_redirs_total': 13, 'node_gets': 7})
    check = Riak('riak', {}, [instance])
    check.check(instance)
    check.check(instance)
    aggregator.assert_metric('riak.node_gets', value=5, tags=instance['tags'])
    aggregator.assert_metric('riak.node_gets', value=7, tags=instance['tags'])
    aggregator.assert_metric('riak.coord_redirs', value=3)
    aggregator.assert_service_check('riak.can_connect', Riak.OK, count=2, tags=check.service_check_tags)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)] * 2


@pytest.mark.parametrize('error', [HTTPClientConnectionError, HTTPClientReadTimeoutError, HTTPClientStatusError])
def test_http_failure_reports_critical(aggregator, instance, fake_http, error):
    endpoint = instance['url']
    fake_http.register_response('GET', endpoint, error('unavailable'))
    check = Riak('riak', {}, [instance])
    with pytest.raises(error, match='unavailable'):
        check.check(instance)
    aggregator.assert_service_check('riak.can_connect', Riak.CRITICAL, tags=check.service_check_tags)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]
