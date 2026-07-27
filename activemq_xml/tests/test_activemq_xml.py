# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from itertools import product

import pytest

from datadog_checks.activemq_xml import ActiveMQXML
from datadog_checks.activemq_xml.activemq_xml import QUEUE_URL
from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPConnectTimeoutError,
    HTTPReadTimeoutError,
)
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CHECK_NAME, CONFIG, GENERAL_METRICS, QUEUE_METRICS, SUBSCRIBER_METRICS, TOPIC_METRICS, URL


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_integration(aggregator, dd_run_check):
    """
    Collect ActiveMQ metrics
    """
    check = ActiveMQXML(CHECK_NAME, {}, [CONFIG])
    dd_run_check(check)

    _test_check(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)

    _test_check(aggregator)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def _test_check(aggregator):
    tags = ["url:{}".format(URL)]

    # Test metrics
    for mname in GENERAL_METRICS:
        aggregator.assert_metric(mname, count=1, tags=tags)

    for mname in QUEUE_METRICS:
        aggregator.assert_metric(mname, count=1, tags=tags + ["queue:my_queue"])

    for mname, tname in product(TOPIC_METRICS, ["my_topic", "ActiveMQ.Advisory.MasterBroker"]):
        aggregator.assert_metric(mname, count=1, tags=tags + ["topic:{}".format(tname)])

    for mname in SUBSCRIBER_METRICS:
        subscriber_tags = tags + [
            "clientId:my_client",
            "connectionId:NOTSET",
            "subscriptionName:my_subscriber",
            "destinationName:my_topic",
            "selector:jms_selector",
            "active:no",
        ]
        aggregator.assert_metric(mname, count=1, tags=subscriber_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize('error_cls', [HTTPConnectionError, HTTPConnectTimeoutError])
def test_suppress_errors_handles_connection_failures(mock_http, error_cls):
    check = ActiveMQXML(CHECK_NAME, {}, [CONFIG])
    mock_http.get.side_effect = error_cls('unreachable')

    assert check._fetch_data(URL, QUEUE_URL, suppress_errors=True) is False


def test_suppress_errors_does_not_hide_read_timeout(mock_http):
    check = ActiveMQXML(CHECK_NAME, {}, [CONFIG])
    mock_http.get.side_effect = HTTPReadTimeoutError('slow')

    with pytest.raises(HTTPReadTimeoutError, match='slow'):
        check._fetch_data(URL, QUEUE_URL, suppress_errors=True)
