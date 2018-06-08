# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from itertools import product

from datadog_checks.activemq_xml import ActiveMQXML
from .common import CHECK_NAME, CONFIG, URL, GENERAL_METRICS, QUEUE_METRICS, TOPIC_METRICS, SUBSCRIBER_METRICS


def test_check(aggregator):
    """
    Collect ActiveMQ metrics
    """
    check = ActiveMQXML(CHECK_NAME, {}, {})
    check.check(CONFIG)

    tags = ["url:{}".format(URL)]

    print(1)
    # Test metrics
    for mname in GENERAL_METRICS:
        aggregator.assert_metric(mname, count=1, tags=tags)

    print(2)
    for mname in QUEUE_METRICS:
        aggregator.assert_metric(mname, count=1, tags=tags + ["queue:my_queue"])

    print(3)
    for mname, tname in product(TOPIC_METRICS, ["my_topic", "ActiveMQ.Advisory.MasterBroker"]):
        aggregator.assert_metric(mname, count=1, tags=tags + ["topic:{}".format(tname)])

    print(4)
    for mname in SUBSCRIBER_METRICS:
        subscriber_tags = tags + [
            "clientId:my_client",
            "connectionId:NOTSET",
            "subscriptionName:my_subscriber",
            "destinationName:my_topic",
            "selector:jms_selector",
            "active:no"
        ]
        aggregator.assert_metric(mname, count=1, tags=subscriber_tags)

    print(5)
    aggregator.assert_all_metrics_covered()
