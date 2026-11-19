# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.activemq_xml import ActiveMQXML
from datadog_checks.activemq_xml.activemq_xml import QUEUE_URL, SUBSCRIBER_URL, TOPIC_URL
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientConnectTimeoutError

from .common import CHECK_NAME

URL = 'http://localhost:8161'


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(HTTPClientConnectionError('Connection refused'), id='connection'),
        pytest.param(HTTPClientConnectTimeoutError('Connect timed out'), id='connect-timeout'),
    ],
)
def test_suppress_errors_skips_unreachable_broker(dd_run_check, aggregator, fake_http, error):
    for path in (QUEUE_URL, TOPIC_URL, SUBSCRIBER_URL):
        fake_http.register_response('GET', URL + path, error)
    check = ActiveMQXML(CHECK_NAME, {}, [{'url': URL, 'suppress_errors': True}])

    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    assert len(fake_http.requests) == 3
