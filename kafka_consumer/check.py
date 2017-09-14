# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import time

# 3p
from kafka import SimpleClient
from kafka.structs import OffsetRequestPayload
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError

# project
from checks import AgentCheck

DEFAULT_KAFKA_TIMEOUT = 5
DEFAULT_ZK_TIMEOUT = 5

CONTEXT_UPPER_BOUND = 100


class KafkaCheck(AgentCheck):
    """
    Check Consumer Lag for Kafka consumers that store their offsets in Zookeeper.

    Modern Kafka consumers store their offset in Kafka rather than Zookeeper,
    but support for this has not been added yet. It's tricky because this check
    is much simpler if it assumes a single place can be queried for all consumer
    offsets, but currently there's no easy way to do that. Once KIP-88 is
    implemented, it will be much easier to add this functionality, although it
    would only work for Kafka brokers >= 0.10.2.0. In the meantime, you can
    instrument your individual kafka consumers to submit their offsets to
    Datadog.
    """

    SOURCE_TYPE_NAME = 'kafka'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        self.zk_timeout = int(
            init_config.get('zk_timeout', DEFAULT_ZK_TIMEOUT))
        self.kafka_timeout = int(
            init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT))

    def _get_highwater_offsets(self, kafka_hosts_ports):
        """
        Fetch highwater offsets for each topic/partition from Kafka cluster.

        Do this for all partitions in the cluster because even if it has no
        consumers, we may want to measure whether producers are successfully
        producing. No need to limit this for performance because fetching broker
        offsets from Kafka is a relatively inexpensive operation.
        """
        kafka_conn = SimpleClient(kafka_hosts_ports, timeout=self.kafka_timeout)
        try:
            broker_topics_partitions = kafka_conn.topics_to_brokers.keys()
            # batch a bunch of requests into a single network call
            offsets_request = [OffsetRequestPayload(topic, partition, -1, 1)
                for topic, partition in broker_topics_partitions]
            offsets_response = kafka_conn.send_offset_request(offsets_request)
            highwater_offsets = {(x.topic, x.partition): x.offsets[0] for x in offsets_response}
        finally:
            try:
                kafka_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Kafka connection')
        return highwater_offsets

    def _get_zk_path_children(self, zk_conn, zk_path, name_for_error):
        """Fetch child nodes for a given Zookeeper path."""
        children = []
        try:
            children = zk_conn.get_children(zk_path)
        except NoNodeError:
            self.log.info('No zookeeper node at %s', zk_path)
        except Exception:
            self.log.exception('Could not read %s from %s', name_for_error, zk_path)
        return children

    def _get_zk_consumer_offsets(self, zk_hosts_ports, consumer_groups=None, zk_prefix=''):
        """
        Fetch Consumer Group offsets from Zookeeper.

        Also fetch consumer_groups, topics, and partitions if not
        already specified in consumer_groups.

        :param dict consumer_groups: The consumer groups, topics, and partitions
            that you want to fetch offsets for. If consumer_groups is None, will
            fetch offsets for all consumer_groups. For examples of what this
            dict can look like, see _validate_consumer_groups().
        """
        zk_consumer_offsets = {}

        # Construct the Zookeeper path pattern
        # /consumers/[groupId]/offsets/[topic]/[partitionId]
        zk_path_consumer = zk_prefix + '/consumers/'
        zk_path_topic_tmpl = zk_path_consumer + '{group}/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '{topic}/'

        zk_conn = KazooClient(zk_hosts_ports, timeout=self.zk_timeout)
        zk_conn.start()
        try:
            if consumer_groups is None:
                # If consumer groups aren't specified, fetch them from ZK
                consumer_groups = {consumer_group: None for consumer_group in
                    self._get_zk_path_children(zk_conn, zk_path_consumer, 'consumer groups')}

            for consumer_group, topics in consumer_groups.iteritems():
                if topics is None:
                    # If topics are't specified, fetch them from ZK
                    zk_path_topics = zk_path_topic_tmpl.format(group=consumer_group)
                    topics = {topic: None for topic in
                        self._get_zk_path_children(zk_conn, zk_path_topics, 'topics')}

                for topic, partitions in topics.iteritems():
                    if partitions is not None:
                        partitions = set(partitions)  # defend against bad user input
                    else:
                        # If partitions aren't specified, fetch them from ZK
                        zk_path_partitions = zk_path_partition_tmpl.format(
                            group=consumer_group, topic=topic)
                        # Zookeeper returns the partition IDs as strings because
                        # they are extracted from the node path
                        partitions = [int(x) for x in self._get_zk_path_children(
                            zk_conn, zk_path_partitions, 'partitions')]

                    # Fetch consumer offsets for each partition from ZK
                    for partition in partitions:
                        zk_path = (zk_path_partition_tmpl + '{partition}/').format(
                            group=consumer_group, topic=topic, partition=partition)
                        try:
                            consumer_offset = int(zk_conn.get(zk_path)[0])
                            key = (consumer_group, topic, partition)
                            zk_consumer_offsets[key] = consumer_offset
                        except NoNodeError:
                            self.log.info('No zookeeper node at %s', zk_path)
                        except Exception:
                            self.log.exception('Could not read consumer offset from %s', zk_path)
        finally:
            try:
                zk_conn.stop()
                zk_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Zookeeper connection')
        return zk_consumer_offsets

    def check(self, instance):
        # For calculating lag, we have to fetch offsets from both kafka and
        # zookeeper. There's a potential race condition because whichever one we
        # check first may be outdated by the time we check the other. Better to
        # check consumer offset before checking broker offset because worst case
        # is that overstates consumer lag a little. Doing it the other way can
        # understate consumer lag to the point of having negative consumer lag,
        # which just creates confusion because it's theoretically impossible.

        # Fetch consumer group offsets from Zookeeper
        zk_hosts_ports = self._read_config(instance, 'zk_connect_str')
        zk_prefix = instance.get('zk_prefix', '')

        # If monitor_unlisted_consumer_groups is True, fetch all groups stored in ZK
        if instance.get('monitor_unlisted_consumer_groups', False):
            consumer_groups = None
        else:
            consumer_groups = self._validate_consumer_groups(
                self._read_config(instance, 'consumer_groups'))

        consumer_offsets = self._get_zk_consumer_offsets(
            zk_hosts_ports, consumer_groups, zk_prefix)

        if len(consumer_offsets) > CONTEXT_UPPER_BOUND:
            self.log.warning("Discovered %s contexts - this exceeds the maximum number of "
                             "contexts permitted by the check. Please narrow your target by "
                             "specifying in your YAML what consumer groups, topics and "
                             "partitions you wish to monitor.", len(consumer_offsets))
            return

        # Fetch the broker highwater offsets
        kafka_hosts_ports = self._read_config(instance, 'kafka_connect_str')
        highwater_offsets = self._get_highwater_offsets(kafka_hosts_ports)

        # Report the broker highwater offset
        for (topic, partition), highwater_offset in highwater_offsets.iteritems():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            self.gauge('kafka.broker_offset', highwater_offset, tags=broker_tags)

        # Report the consumer group offsets and consumer lag
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.iteritems():
            if (topic, partition) not in highwater_offsets:
                self.log.debug("[%s] topic: %s partition: %s was not available in the broker "
                               "- skipping consumer submission", consumer_group, topic, partition)
                continue

            consumer_group_tags = ['topic:%s' % topic, 'partition:%s' % partition,
                'consumer_group:%s' % consumer_group]
            self.gauge('kafka.consumer_offset', consumer_offset, tags=consumer_group_tags)
            if (topic, partition) not in highwater_offsets:
                self.log.warn("Consumer offsets exist for topic: %s "
                    "partition: %s but that topic partition doesn't "
                    "actually exist in the cluster.", topic, partition)
                continue
            consumer_lag = highwater_offsets[(topic, partition)] - consumer_offset
            if consumer_lag < 0:
                # this will result in data loss, so emit an event for max visibility
                title = "Negative consumer lag for group: {group}.".format(group=consumer_group)
                message = "Consumer lag for Kafka consumer group: {group}, topic: {topic}, " \
                    "partition: {partition} is negative.\n\n" \
                    "This is theoretically impossible, yet may occur and will " \
                    "result in data loss because the consumer group will miss " \
                    "all messages produced to the partition until the lag turns " \
                    "positive.".format(
                        group=consumer_group,
                        topic=topic,
                        partition=partition
                    )
                key = "{}:{}:{}".format(consumer_group, topic, partition)
                self._send_event(title, message, consumer_group_tags, 'consumer_lag',
                    key, severity="error")
                self.log.debug(message)

            self.gauge('kafka.consumer_lag', consumer_lag,
               tags=consumer_group_tags)

    @staticmethod
    def _read_config(instance, key):
        val = instance.get(key)
        if val is None:
            raise Exception('Must provide `%s` value in instance config' % key)

        return val

    def _validate_consumer_groups(self, val):
        # val = {'consumer_group': {'topic': [0, 1]}}
        # consumer groups are optional
        assert isinstance(val, dict) or val is None
        if val is not None:
            for consumer_group, topics in val.iteritems():
                assert isinstance(consumer_group, basestring)
                # topics are optional
                assert isinstance(topics, dict) or topics is None
                if topics is not None:
                    for topic, partitions in topics.iteritems():
                        assert isinstance(topic, basestring)
                        # partitions are optional
                        assert isinstance(partitions, (list, tuple)) or partitions is None
                        if partitions is not None:
                            for partition in partitions:
                                assert isinstance(partition, int)
        return val

    def _send_event(self, title, text, tags, type, aggregation_key, severity='info'):
        """Emit an event to the Datadog Event Stream."""
        event_dict = {
            'timestamp': int(time.time()),
            'source_type_name': self.SOURCE_TYPE_NAME,
            'msg_title': title,
            'event_type': type,
            'alert_type': severity,
            'msg_text': text,
            'tags': tags,
            'aggregation_key': aggregation_key,
        }
        self.event(event_dict)
