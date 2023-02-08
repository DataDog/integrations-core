# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import pytest

from datadog_checks.kafka_consumer import KafkaCheck

from .common import HOST, PARTITIONS, TOPICS, is_supported

pytestmark = pytest.mark.skipif(
    not is_supported('zookeeper'), reason='zookeeper consumer offsets not supported in current environment'
)


BROKER_METRICS = ['kafka.broker_offset']

CONSUMER_METRICS = ['kafka.consumer_offset', 'kafka.consumer_lag']


@pytest.mark.usefixtures('dd_environment')
def test_check_zk_basic_case_integration(aggregator, zk_instance, dd_run_check):
    return True
#     """
#     Testing Kafka_consumer check.
#     """
#     kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [zk_instance])
#     dd_run_check(kafka_consumer_check)

#     _assert_check_zk_basic_case(aggregator, zk_instance)


# @pytest.mark.e2e
# def test_check_zk_basic_case_e2e(dd_agent_check, zk_instance):
#     aggregator = dd_agent_check(zk_instance)

#     _assert_check_zk_basic_case(aggregator, zk_instance)


# def _assert_check_zk_basic_case(aggregator, zk_instance):
#     for name, consumer_group in zk_instance['consumer_groups'].items():
#         for topic, partitions in consumer_group.items():
#             for partition in partitions:
#                 tags = ["topic:{}".format(topic), "partition:{}".format(partition)]
#                 for mname in BROKER_METRICS:
#                     aggregator.assert_metric(mname, tags=tags, at_least=1)
#                 for mname in CONSUMER_METRICS:
#                     aggregator.assert_metric(
#                         mname, tags=tags + ["source:zk", "consumer_group:{}".format(name)], at_least=1
#                     )

#     aggregator.assert_all_metrics_covered()


# @pytest.mark.usefixtures('dd_environment')
# def test_multiple_servers_zk(aggregator, zk_instance, dd_run_check):
#     """
#     Testing Kafka_consumer check.
#     """
#     multiple_server_zk_instance = copy.deepcopy(zk_instance)
#     multiple_server_zk_instance['kafka_connect_str'] = [
#         multiple_server_zk_instance['kafka_connect_str'],
#         '{}:9092'.format(HOST),
#     ]

#     kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [multiple_server_zk_instance])
#     dd_run_check(kafka_consumer_check)

#     for name, consumer_group in multiple_server_zk_instance['consumer_groups'].items():
#         for topic, partitions in consumer_group.items():
#             for partition in partitions:
#                 tags = ["topic:{}".format(topic), "partition:{}".format(partition)]
#                 for mname in BROKER_METRICS:
#                     aggregator.assert_metric(mname, tags=tags, at_least=1)
#                 for mname in CONSUMER_METRICS:
#                     aggregator.assert_metric(
#                         mname, tags=tags + ["source:zk", "consumer_group:{}".format(name)], at_least=1
#                     )

#     aggregator.assert_all_metrics_covered()


# @pytest.mark.usefixtures('dd_environment')
# def test_check_no_groups_zk(aggregator, zk_instance, dd_run_check):
#     """
#     Testing Kafka_consumer check grabbing groups from ZK
#     """
#     nogroup_instance = copy.deepcopy(zk_instance)
#     nogroup_instance.pop('consumer_groups')
#     nogroup_instance['monitor_unlisted_consumer_groups'] = True

#     kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [nogroup_instance])
#     dd_run_check(kafka_consumer_check)

#     for topic in TOPICS:
#         for partition in PARTITIONS:
#             tags = ["topic:{}".format(topic), "partition:{}".format(partition)]
#             for mname in BROKER_METRICS:
#                 aggregator.assert_metric(mname, tags=tags, at_least=1)
#             for mname in CONSUMER_METRICS:
#                 aggregator.assert_metric(mname, tags=tags + ['source:zk', 'consumer_group:my_consumer'], at_least=1)

#     aggregator.assert_all_metrics_covered()


# @pytest.mark.usefixtures('dd_environment')
# def test_check_no_partitions_zk(aggregator, zk_instance, dd_run_check):
#     """
#     Testing Kafka_consumer check grabbing partitions from ZK
#     """
#     no_partitions_instance = copy.deepcopy(zk_instance)
#     topic = 'marvel'
#     no_partitions_instance['consumer_groups'] = {'my_consumer': {topic: []}}

#     kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [no_partitions_instance])
#     dd_run_check(kafka_consumer_check)

#     for partition in PARTITIONS:
#         tags = ["topic:{}".format(topic), "partition:{}".format(partition)]
#         for mname in BROKER_METRICS:
#             aggregator.assert_metric(mname, tags=tags, at_least=1)
#         for mname in CONSUMER_METRICS:
#             aggregator.assert_metric(mname, tags=tags + ['source:zk', 'consumer_group:my_consumer'], at_least=1)

#     aggregator.assert_all_metrics_covered()
