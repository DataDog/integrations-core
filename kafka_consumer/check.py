# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict

# 3p
from kafka import KafkaClient
from kafka.common import OffsetRequestPayload as OffsetRequest
from kafka.structs import OffsetFetchRequestPayload
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError

# project
from config import _is_affirmative
from checks import AgentCheck

DEFAULT_KAFKA_TIMEOUT = 5
DEFAULT_ZK_TIMEOUT = 5
DEFAULT_ZK_OFFSETS = True


class KafkaCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'kafka'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        self.zk_timeout = int(
            init_config.get('zk_timeout', DEFAULT_ZK_TIMEOUT))
        self.kafka_timeout = int(
            init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT))

    def check(self, instance):
        consumer_groups = self.read_config(instance, 'consumer_groups',
                                           cast=self._validate_consumer_groups)
        zk_offsets = _is_affirmative(instance.get('zk_offsets', True))
        zk_connect_str = self.read_config(instance, 'zk_connect_str')
        kafka_host_ports = self.read_config(instance, 'kafka_connect_str')

        # Construct the Zookeeper path pattern
        zk_prefix = instance.get('zk_prefix', '')
        zk_path_tmpl = zk_prefix + '/consumers/%s/offsets/%s/%s'

        # Connect to Zookeeper
        zk_conn = KazooClient(zk_connect_str, timeout=self.zk_timeout)
        zk_conn.start()

        consumer_offsets = {}
        topics = defaultdict(set)
        try:
            if zk_offsets:
                topics, consumer_offsets = self.get_offsets_zk(zk_connect_str, consumer_groups, zk_prefix='')
            else:
                topics, consumer_offsets = self.get_offsets_kafka(kafka_host_ports, consumer_groups)
        except Exception:
            self.log.warn('There was an issue collecting the consumer offsets, metrics may be missing.')

        # Connect to Kafka
        kafka_conn = KafkaClient(kafka_host_ports, timeout=self.kafka_timeout)

        try:
            # Query Kafka for the broker offsets
            broker_offsets = {}
            for topic, partitions in topics.items():
                offset_responses = kafka_conn.send_offset_request([
                    OffsetRequest(topic, p, -1, 1) for p in partitions])

                for resp in offset_responses:
                    broker_offsets[(resp.topic, resp.partition)] = resp.offsets[0]
        finally:
            try:
                kafka_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Kafka connection')

        # Report the broker data
        for (topic, partition), broker_offset in broker_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            broker_offset = broker_offsets.get((topic, partition))
            self.gauge('kafka.broker_offset', broker_offset, tags=broker_tags)

        # Report the consumer
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.items():

            # Get the broker offset
            broker_offset = broker_offsets.get((topic, partition))

            # Report the consumer offset and lag
            tags = ['topic:%s' % topic, 'partition:%s' % partition,
                    'consumer_group:%s' % consumer_group]
            self.gauge('kafka.consumer_offset', consumer_offset, tags=tags)
            self.gauge('kafka.consumer_lag', broker_offset - consumer_offset,
                       tags=tags)

    # Private config validation/marshalling functions

    def _validate_consumer_groups(self, val):
        try:
            consumer_group, topic_partitions = val.items()[0]
            assert isinstance(consumer_group, (str, unicode))
            topic, partitions = topic_partitions.items()[0]
            assert isinstance(topic, (str, unicode))
            assert isinstance(partitions, (list, tuple))
            return val
        except Exception as e:
            self.log.exception(e)
            raise Exception('''The `consumer_groups` value must be a mapping of mappings, like this:
consumer_groups:
  myconsumer0: # consumer group name
    mytopic0: [0, 1] # topic: list of partitions
  myconsumer1:
    mytopic0: [0, 1, 2]
    mytopic1: [10, 12]
''')

    def get_offsets_zk(self, zk_connect_str, consumer_groups, zk_prefix=''):
        # Construct the Zookeeper path pattern
        zk_path_tmpl = zk_prefix + '/consumers/%s/offsets/%s/%s'

        # Connect to Zookeeper
        zk_conn = KazooClient(zk_connect_str, timeout=self.zk_timeout)
        zk_conn.start()

        try:
            # Query Zookeeper for consumer offsets
            consumer_offsets = {}
            topics = defaultdict(set)
            for consumer_group, topic_partitions in consumer_groups.iteritems():
                for topic, partitions in topic_partitions.iteritems():
                    # Remember the topic partitions that we've see so that we can
                    # look up their broker offsets later
                    topics[topic].update(set(partitions))
                    for partition in partitions:
                        zk_path = zk_path_tmpl % (consumer_group, topic, partition)
                        try:
                            consumer_offset = int(zk_conn.get(zk_path)[0])
                            key = (consumer_group, topic, partition)
                            consumer_offsets[key] = consumer_offset
                        except NoNodeError:
                            self.log.warn('No zookeeper node at %s' % zk_path)
                        except Exception:
                            self.log.exception('Could not read consumer offset from %s' % zk_path)
        finally:
            try:
                zk_conn.stop()
                zk_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Zookeeper connection')

        return topics, consumer_offsets

    def get_offsets_kafka(self, kafka_connect_str, consumer_groups):
        consumer_offsets = {}
        topics = defaultdict(set)
        for consumer_group, topic_partitions in consumer_groups.iteritems():
            try:
                coordinator = self.get_group_coordinator(kafka_connect_str, consumer_group)
                offsets = self.get_consumer_offsets(coordinator, consumer_group, topic_partitions)
                for topic_partition, offset in offsets.iteritems():
                    topic, partition = topic_partition
                    topics[topic].updata([partition])
                    key = (consumer_group, topic, partition)
                    consumer_offsets[key] = offset
            except Exception:
                self.log.expcetion('Could not read consumer offsets from kafka.')

        return topics, consumer_offsets

    def get_group_coordinator(self, kafka_connect_str, group):
        kafka_cli = KafkaClient(kafka_connect_str, timeout=self.kafka_timeout)

        return kafka_cli._get_coordinator_for_group(group)

    def get_consumer_offsets(self, coordinator, group, topic_partitions):
        conn_str = "{}:{}".format(coordinator.host, coordinator.port)
        kafka_cli = KafkaClient(conn_str, timeout=self.kafka_timeout)

        requests = []
        for topic, partitions in topic_partitions.iteritems():
            requests.extend([OffsetFetchRequestPayload(topic=topic, partition=p) for p in partitions])

        responses = kafka_cli.send_offset_fetch_request_kafka(group, payloads=requests)

        consumer_offsets = {}
        for resp in responses:
            consumer_offsets[(resp.topic, resp.partition)] = resp.offset

        return consumer_offsets
