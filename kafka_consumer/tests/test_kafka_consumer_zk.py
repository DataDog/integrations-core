# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import pytest

from datadog_checks.kafka_consumer import KafkaCheck

from .common import HOST, KAFKA_CONNECT_STR, PARTITIONS, TOPICS, ZK_CONNECT_STR, is_supported

pytestmark = pytest.mark.skipif(
    not is_supported('zookeeper'), reason='zookeeper consumer offsets not supported in current environment'
)


BROKER_METRICS = ['kafka.broker_offset']

CONSUMER_METRICS = ['kafka.consumer_offset', 'kafka.consumer_lag']


@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_check_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [zk_instance])
    kafka_consumer_check.check(zk_instance)

    for name, consumer_group in zk_instance['consumer_groups'].items():
        for topic, partitions in consumer_group.items():
            for partition in partitions:
                tags = ["topic:{}".format(topic), "partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(
                        mname, tags=tags + ["source:zk", "consumer_group:{}".format(name)], at_least=1
                    )

    # let's reassert for the __consumer_offsets - multiple partitions
    aggregator.assert_metric('kafka.broker_offset', at_least=1)
    aggregator.assert_all_metrics_covered()

    all_partitions = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'zk_connect_str': ZK_CONNECT_STR,
        'consumer_groups': {'my_consumer': {'marvel': []}},
    }
    kafka_consumer_check.check(all_partitions)
    aggregator.assert_metric(
        'kafka.consumer_offset',
        tags=['topic:marvel', 'partition:0', 'consumer_group:my_consumer', 'source:zk'],
        at_least=1,
    )
    aggregator.assert_metric(
        'kafka.consumer_offset',
        tags=['topic:marvel', 'partition:1', 'consumer_group:my_consumer', 'source:zk'],
        at_least=1,
    )


@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_multiple_servers_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check.
    """
    multiple_server_zk_instance = copy.deepcopy(zk_instance)
    multiple_server_zk_instance['kafka_connect_str'] = [
        multiple_server_zk_instance['kafka_connect_str'],
        '{}:9092'.format(HOST),
    ]

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [multiple_server_zk_instance])
    kafka_consumer_check.check(multiple_server_zk_instance)

    for name, consumer_group in multiple_server_zk_instance['consumer_groups'].items():
        for topic, partitions in consumer_group.items():
            for partition in partitions:
                tags = ["topic:{}".format(topic), "partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(
                        mname, tags=tags + ["source:zk", "consumer_group:{}".format(name)], at_least=1
                    )

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment', 'kafka_producer', 'zk_consumer')
def test_check_nogroups_zk(aggregator, zk_instance):
    """
    Testing Kafka_consumer check grabbing groups from ZK
    """
    nogroup_instance = copy.deepcopy(zk_instance)
    nogroup_instance.pop('consumer_groups')
    nogroup_instance['monitor_unlisted_consumer_groups'] = True

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [nogroup_instance])
    kafka_consumer_check.check(nogroup_instance)

    for topic in TOPICS:
        if topic != '__consumer_offsets':
            for partition in PARTITIONS:
                tags = ["topic:{}".format(topic), "partition:{}".format(partition)]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=tags + ['source:zk', 'consumer_group:my_consumer'], at_least=1)
        else:
            for mname in BROKER_METRICS + CONSUMER_METRICS:
                aggregator.assert_metric(mname, at_least=1)

    aggregator.assert_all_metrics_covered()
