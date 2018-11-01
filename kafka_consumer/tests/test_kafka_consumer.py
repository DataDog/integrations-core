# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import pytest
from six import iteritems

from datadog_checks.kafka_consumer import KafkaCheck
from .common import is_supported

pytestmark = pytest.mark.skipif(
    not is_supported('kafka'),
    reason='kafka consumer offsets not supported in current environment'
)


BROKER_METRICS = [
    'kafka.broker_offset',
]

CONSUMER_PARTITION_LAG_METRIC = 'kafka.consumer_lag'

CONSUMER_METRICS = [
    'kafka.consumer_offset',
    CONSUMER_PARTITION_LAG_METRIC
]

CONSUMER_TOPIC_METRICS = [
    'kafka.consumer_lag.total',
]


@pytest.mark.usefixtures('dd_environment', 'kafka_consumer', 'kafka_producer')
def test_check_kafka(aggregator, kafka_instance):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(kafka_instance)

    for name, consumer_group in iteritems(kafka_instance['consumer_groups']):
        for topic, partitions in iteritems(consumer_group):
            tags = ["topic:{}".format(topic)] + ['optional:tag1']
            consumer_tags = ["source:kafka", "consumer_group:{}".format(name)]

            for mname in CONSUMER_TOPIC_METRICS:
                aggregator.assert_metric(mname, tags=(tags + consumer_tags), count=0)

            for partition in partitions:
                tags += ["partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=(tags + consumer_tags), at_least=1)

    # let's reassert for the __consumer_offsets - multiple partitions
    aggregator.assert_metric('kafka.broker_offset', at_least=1)


@pytest.mark.usefixtures('dd_environment', 'kafka_consumer', 'kafka_producer')
def test_aggregate_lag_kafka(aggregator, kafka_instance):
    """
    Testing Kafka_consumer check.
    """
    aggregate_lag_kafka_instance = copy.deepcopy(kafka_instance)
    aggregate_lag_kafka_instance['aggregate_consumer_lag'] = True

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(aggregate_lag_kafka_instance)

    for name, consumer_group in iteritems(aggregate_lag_kafka_instance['consumer_groups']):
        for topic, partitions in iteritems(consumer_group):
            tags = ["topic:{}".format(topic)] + ['optional:tag1']
            consumer_tags = ["source:kafka", "consumer_group:{}".format(name)]

            for mname in CONSUMER_TOPIC_METRICS:
                aggregator.assert_metric(mname, tags=(tags + consumer_tags), at_least=1)

            for partition in partitions:
                tags += ["partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=(tags + consumer_tags), at_least=1)

    # let's reassert for the __consumer_offsets - multiple partitions
    aggregator.assert_metric('kafka.broker_offset', at_least=1)


@pytest.mark.usefixtures('dd_environment', 'kafka_consumer', 'kafka_producer')
def test_no_partition_lag_kafka(aggregator, kafka_instance):
    """
    Testing Kafka_consumer check.
    """
    no_partition_lag_kafka_instance = copy.deepcopy(kafka_instance)
    no_partition_lag_kafka_instance['aggregate_consumer_lag'] = True
    no_partition_lag_kafka_instance['per_partition_consumer_lag'] = False

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(no_partition_lag_kafka_instance)

    for name, consumer_group in iteritems(no_partition_lag_kafka_instance['consumer_groups']):
        for topic, partitions in iteritems(consumer_group):
            tags = ["topic:{}".format(topic)] + ['optional:tag1']
            consumer_tags = ["source:kafka", "consumer_group:{}".format(name)]

            for mname in CONSUMER_TOPIC_METRICS:
                aggregator.assert_metric(mname, tags=(tags + consumer_tags), at_least=1)

            for partition in partitions:
                tags += ["partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    assertion = {'count': 0} if mname == CONSUMER_PARTITION_LAG_METRIC else {'at_least': 1}
                    aggregator.assert_metric(mname, tags=(tags + consumer_tags), **assertion)

    # let's reassert for the __consumer_offsets - multiple partitions
    aggregator.assert_metric('kafka.broker_offset', at_least=1)
