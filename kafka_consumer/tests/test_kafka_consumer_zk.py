# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import time

import pytest
from six import iteritems

from datadog_checks.base.utils.containers import hash_mutable
from datadog_checks.kafka_consumer import KafkaCheck
from .common import HOST, PARTITIONS, TOPICS, ZK_CONNECT_STR, is_supported

pytestmark = pytest.mark.skipif(
    not is_supported('zookeeper'),
    reason='zookeeper consumer offsets not supported in current environment'
)


BROKER_METRICS = [
    'kafka.broker_offset',
]

CONSUMER_METRICS = [
    'kafka.consumer_offset',
    'kafka.consumer_lag',
]


@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_check_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(zk_instance)

    for name, consumer_group in iteritems(zk_instance['consumer_groups']):
        for topic, partitions in iteritems(consumer_group):
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
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_multiple_servers_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check.
    """
    multiple_server_zk_instance = copy.deepcopy(zk_instance)
    multiple_server_zk_instance['kafka_connect_str'] = [
        multiple_server_zk_instance['kafka_connect_str'],
        '{}:9092'.format(HOST)]

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(multiple_server_zk_instance)

    for name, consumer_group in iteritems(multiple_server_zk_instance['consumer_groups']):
        for topic, partitions in iteritems(consumer_group):
            for partition in partitions:
                tags = ["topic:{}".format(topic),
                        "partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=tags +
                                             ["source:zk", "consumer_group:{}".format(name)], at_least=1)

    aggregator.assert_all_metrics_covered()

@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_check_nogroups_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check grabbing groups from ZK
    """
    nogroup_instance = copy.deepcopy(zk_instance)
    nogroup_instance.pop('consumer_groups')
    nogroup_instance['monitor_unlisted_consumer_groups'] = True

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(nogroup_instance)

    for topic in TOPICS:
        if topic != '__consumer_offsets':
            for partition in PARTITIONS:
                tags = ["topic:{}".format(topic),
                        "partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=tags + ['source:zk', 'consumer_group:my_consumer'], at_least=1)
        else:
            for mname in BROKER_METRICS + CONSUMER_METRICS:
                aggregator.assert_metric(mname, at_least=1)

    aggregator.assert_all_metrics_covered()

def test_should_zk():
    check = KafkaCheck('kafka_consumer', {}, {})
    # Kafka Consumer Offsets set to True and we have a zk_connect_str that hasn't been run yet
    assert (check._should_zk([ZK_CONNECT_STR, ZK_CONNECT_STR], 10, True) is True)
    # Kafka Consumer Offsets is set to False, should immediately ZK
    assert (check._should_zk(ZK_CONNECT_STR, 10, False) is True)
    # Last time we checked ZK_CONNECT_STR was less than interval ago, shouldn't ZK
    zk_connect_hash = hash_mutable(ZK_CONNECT_STR)
    check._zk_last_ts[zk_connect_hash] = time.time()
    assert (check._should_zk(ZK_CONNECT_STR, 100, True) is False)
