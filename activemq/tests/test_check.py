# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest


@pytest.mark.e2e
def test(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance)
    metrics = [
        "activemq.queue.avg_enqueue_time",
        "activemq.queue.consumer_count",
        "activemq.queue.producer_count",
        "activemq.queue.max_enqueue_time",
        "activemq.queue.min_enqueue_time",
        "activemq.queue.memory_pct",
        "activemq.queue.size",
        "activemq.queue.dequeue_count",
        "activemq.queue.dispatch_count",
        "activemq.queue.enqueue_count",
        "activemq.queue.expired_count",
        "activemq.queue.in_flight_count",
        "activemq.broker.store_pct",
        "activemq.broker.temp_pct",
        "activemq.broker.memory_pct",
    ]
    for metric in metrics:
        aggregator.assert_metric(metric)
