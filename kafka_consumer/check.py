# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import random
from collections import defaultdict

# 3p
from kafka.client import KafkaClient
from kafka.common import OffsetRequestPayload as LegacyOffsetRequest
from kafka.protocol.commit import OffsetFetchRequest, GroupCoordinatorRequest
from kafka.protocol.offset import OffsetRequest, OffsetResponse_v0
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
    API_VERSION_MAP = [
        ((0, 9), 2),
        ((0, 8, 2), 1)
    ]

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        self.zk_timeout = int(
            init_config.get('zk_timeout', DEFAULT_ZK_TIMEOUT))
        self.kafka_timeout = int(
            init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT))
        self.kafka_clients = {}

    def _get_kafka_client(self, instance):
        kafka_conn_str = self.read_config(instance, 'kafka_connect_str')
        if not kafka_conn_str:
            raise Exception('Bad instance')

        if kafka_conn_str not in self.kafka_clients:
            cli = KafkaClient(bootstrap_servers=kafka_conn_str, client_id='dd-agent')
            self.kafka_clients[kafka_conn_str] = cli

        return self.kafka_clients[kafka_conn_str]

    def check(self, instance):
        consumer_groups = self.read_config(instance, 'consumer_groups',
                                           cast=self._validate_consumer_groups)
        zk_offsets = _is_affirmative(instance.get('zk_offsets', True))
        zk_connect_str = instance.get('zk_connect_str')
        zk_prefix = instance.get('zk_prefix', '')

        consumer_offsets = {}
        topics = defaultdict(set)
        try:
            if not zk_offsets:
                topics, consumer_offsets = self.get_offsets_kafka(instance, consumer_groups)
            elif zk_connect_str:
                topics, consumer_offsets = self.get_offsets_zk(zk_connect_str, consumer_groups, zk_prefix)
            else:
                self.log.warn('No ZK connection string provided, but config specifies collecting from ZK.')
                return
        except Exception:
            self.log.warn('There was an issue collecting the consumer offsets, metrics may be missing.')

        # Connect to Kafka
        cli = self._get_kafka_client(instance)

        try:
            # Query Kafka for the broker offsets
            broker_offsets = {}
            for topic, partitions in topics.items():
                partition_requests = [(p, -1, 1) for p in partitions]
                request = OffsetRequest[0](-1, [(topic, partition_requests)])
                response = self._make_blocking_req(cli, request)

                is_v0 = True
                if not isinstance(response, OffsetResponse_v0):
                    is_v0 = False

                for topic_partition in response.topics:
                    # handle responses - helper named tuple might make sense
                    _topic = topic_partition[0]
                    for partition_offsets in topic_partition[1]:
                        if is_v0:
                            broker_offsets[(_topic, partition_offsets[0])] = partition_offsets[2][0]
                        else:
                            broker_offsets[(_topic, partition_offsets[0])] = partition_offsets[2]
        finally:
            try:
                # we might not need this.
                cli.close()
            except Exception:
                self.log.exception('Error cleaning up Kafka connection')

        # Report the broker data
        for (topic, partition), broker_offset in broker_offsets.iteritems():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            broker_offset = broker_offsets.get((topic, partition))
            self.gauge('kafka.broker_offset', broker_offset, tags=broker_tags)

        # Report the consumer
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.iteritems():

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

    def get_offsets_kafka(self, instance, consumer_groups):
        consumer_offsets = {}
        topics = defaultdict(set)

        cli = self._get_kafka_client(instance)

        for consumer_group, topic_partitions in consumer_groups.iteritems():
            try:
                coordinator_id = self.get_group_coordinator(cli, consumer_group)
                offsets = self.get_consumer_offsets(cli, coordinator_id, consumer_group, topic_partitions)
                for (topic, partition), offset in offsets.iteritems():
                    topics[topic].update([partition])
                    key = (consumer_group, topic, partition)
                    consumer_offsets[key] = offset
            except Exception:
                self.log.expcetion('Could not read consumer offsets from kafka.')

        return topics, consumer_offsets

    def get_api_for_version(self, version):
        for kafka_ver, api_version in self.API_VERSION_MAP:
            if version >= kafka_ver:
                return api_version

        return 0

    def _make_blocking_req(self, client, request, nodeid=None):

        if not nodeid:
            brokers = client.cluster.brokers()
            if not brokers:
                raise Exception('No known available brokers... make this a specific exception')
            nodeid = random.sample(brokers, 1)[0].nodeId

        future = client.send(nodeid, request)
        client.poll(future=future)  # block until we get response.
        assert future.succeeded()
        response = future.value

        return response

    def get_group_coordinator(self, client, group):
        request = GroupCoordinatorRequest[0](group)

        # not all brokers might return a good response... Try all of them
        for broker in client.cluster.brokers():
            try:
                coord_resp = self._make_blocking_req(client, request, nodeid=broker.nodeId)
                if coord_resp:
                    client.cluster.add_group_coordinator(group, coord_resp)
                    return client.cluster.coordinator_for_group(group)
            except AssertionError:
                continue

        return None


    def get_consumer_offsets(self, client, coord_id, consumer_group, topic_partitions):
        version = client.check_version(coord_id)

        tps = defaultdict(set)
        for topic, partitions in topic_partitions.iteritems():
            tps[topic].add(set(partitions))
        request = OffsetFetchRequest[self.get_api_for_version(version)](consumer_group, list(tps.iteritems()))

        response = self._make_blocking_req(client, request, nodeid=coord_id)

        # consumer_offsets = {}
        # for resp in response.topics:
        #     consumer_offsets[(resp.topic, resp.partition)] = resp.offset

        # return consumer_offsets
