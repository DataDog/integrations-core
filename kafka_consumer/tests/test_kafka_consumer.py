# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import time

import pytest

from .common import is_supported
from datadog_checks.kafka_consumer import KafkaCheck


BROKER_METRICS = [
    'kafka.broker_offset',
]

CONSUMER_METRICS = [
    'kafka.consumer_offset',
    'kafka.consumer_lag',
]


@pytest.mark.kafka
def test_check_kafka(kafka_cluster, kafka_producer, kafka_consumer, kafka_instance, aggregator):
    """
    Testing Kafka_consumer check.
    """
    if not is_supported(['kafka']):
        pytest.skip("kafka consumer offsets not supported in current environment")

    if not kafka_producer.is_alive():
        kafka_producer.start()
        time.sleep(5)

    if not kafka_consumer.is_alive():
        kafka_consumer.start()
        time.sleep(5)

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(kafka_instance)

    for name, consumer_group in kafka_instance['consumer_groups'].iteritems():
        for topic, partitions in consumer_group.iteritems():
            for partition in partitions:
                tags = ["topic:{}".format(topic),
                        "partition:{}".format(partition)] + ['optional:tag1']
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=tags +
                                             ["source:kafka", "consumer_group:{}".format(name)], at_least=1)

    # let's reassert for the __consumer_offsets - multiple partitions
    aggregator.assert_metric('kafka.broker_offset', at_least=1)
