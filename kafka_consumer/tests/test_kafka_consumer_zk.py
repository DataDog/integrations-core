# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import pytest
from six import iteritems

from datadog_checks.kafka_consumer import KafkaCheck
from .common import HOST, PARTITIONS, TOPICS, is_supported

pytestmark = pytest.mark.skipif(
    not is_supported('zookeeper'),
    reason='zookeeper consumer offsets not supported in current environment'
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


@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_check_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(zk_instance)

    for name, consumer_group in iteritems(zk_instance['consumer_groups']):
        for topic, partitions in iteritems(consumer_group):
            tags = ["topic:{}".format(topic)]
            consumer_tags = ["source:zk", "consumer_group:{}".format(name)]

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
        if topic is not '__consumer_offsets':
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


@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_aggregate_lag_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check.
    """
    aggregate_lag_zk_instance = copy.deepcopy(zk_instance)
    aggregate_lag_zk_instance['aggregate_consumer_lag'] = True

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(aggregate_lag_zk_instance)

    for name, consumer_group in iteritems(aggregate_lag_zk_instance['consumer_groups']):
        for topic, partitions in iteritems(consumer_group):
            tags = ["topic:{}".format(topic)]
            consumer_tags = ["source:zk", "consumer_group:{}".format(name)]

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


@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_no_partition_lag_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check.
    """
    no_partition_lag_zk_instance = copy.deepcopy(zk_instance)
    no_partition_lag_zk_instance['aggregate_consumer_lag'] = True
    no_partition_lag_zk_instance['per_partition_consumer_lag'] = False

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, {})
    kafka_consumer_check.check(no_partition_lag_zk_instance)

    for name, consumer_group in iteritems(no_partition_lag_zk_instance['consumer_groups']):
        for topic, partitions in iteritems(consumer_group):
            tags = ["topic:{}".format(topic)]
            consumer_tags = ["source:zk", "consumer_group:{}".format(name)]

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
