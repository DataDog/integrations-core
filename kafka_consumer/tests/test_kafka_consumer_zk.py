# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import time

import pytest

from .common import is_supported, PARTITIONS, TOPICS, HOST
from datadog_checks.kafka_consumer import KafkaCheck


BROKER_METRICS = [
    'kafka.broker_offset',
]

CONSUMER_METRICS = [
    'kafka.consumer_offset',
    'kafka.consumer_lag',
]


@pytest.mark.zookeeper
def test_check_zk(kafka_cluster, kafka_producer, zk_consumer, zk_instance, aggregator):
    """
    Testing Kafka_consumer check.
    """
    if not is_supported(['zookeeper']):
        pytest.skip("zookeeper consumer offsets not supported in current environment")

    if not kafka_producer.is_alive():
        kafka_producer.start()
        time.sleep(5)

    if not zk_consumer.is_alive():
        zk_consumer.start()
        time.sleep(5)

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(zk_instance)

    for name, consumer_group in zk_instance['consumer_groups'].iteritems():
        for topic, partitions in consumer_group.iteritems():
            for partition in partitions:
                tags = ["topic:{}".format(topic),
                        "partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=tags +
                                             ["source:zk", "consumer_group:{}".format(name)], at_least=1)

    # let's reassert for the __consumer_offsets - multiple partitions
    aggregator.assert_metric('kafka.broker_offset', at_least=1)


@pytest.mark.zookeeper
def test_multiple_servers_zk(kafka_cluster, kafka_producer, zk_consumer, zk_instance, aggregator):
    """
    Testing Kafka_consumer check.
    """
    if not is_supported(['zookeeper']):
        pytest.skip("zookeeper consumer offsets not supported in current environment")

    if not kafka_producer.is_alive():
        kafka_producer.start()
        time.sleep(5)

    if not zk_consumer.is_alive():
        zk_consumer.start()
        time.sleep(5)

    multiple_server_zk_instance = copy.deepcopy(zk_instance)
    multiple_server_zk_instance['kafka_connect_str'] = [
        multiple_server_zk_instance['kafka_connect_str'],
        '{}:9092'.format(HOST)]

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(multiple_server_zk_instance)

    for name, consumer_group in multiple_server_zk_instance['consumer_groups'].iteritems():
        for topic, partitions in consumer_group.iteritems():
            for partition in partitions:
                tags = ["topic:{}".format(topic),
                        "partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=tags +
                                             ["source:zk", "consumer_group:{}".format(name)], at_least=1)


@pytest.mark.zookeeper
def test_check_nogroups_zk(kafka_cluster, kafka_producer, zk_consumer, zk_instance, aggregator):
    """
    Testing Kafka_consumer check grabbing groups from ZK
    """
    if not is_supported(['zookeeper']):
        pytest.skip("zookeeper consumer offsets not supported in current environment")

    if not kafka_producer.is_alive():
        kafka_producer.start()
        time.sleep(5)

    if not zk_consumer.is_alive():
        zk_consumer.start()
        time.sleep(5)

    nogroup_instance = copy.deepcopy(zk_instance)
    nogroup_instance.pop('consumer_groups')
    nogroup_instance['monitor_unlisted_consumer_groups'] = True

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(nogroup_instance)

    for topic in TOPICS:
        if topic is not '__consumer_offsets':
            for partition in PARTITIONS:
                tags = ["topic:{}".format(topic),
                        "partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                    for mname in CONSUMER_METRICS:
                        aggregator.assert_metric(mname, tags=tags +
                                                 ["source:zk", "consumer_group:my_consumer"], at_least=1)
        else:
            for mname in BROKER_METRICS + CONSUMER_METRICS:
                aggregator.assert_metric(mname, at_least=1)
