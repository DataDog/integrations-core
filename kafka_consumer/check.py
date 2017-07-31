# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
import time

# 3p
from kafka.client import KafkaClient
from kafka.protocol.offset import OffsetRequest
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError

# project
from checks import AgentCheck


DEFAULT_KAFKA_TIMEOUT = 5
DEFAULT_ZK_TIMEOUT = 5


class KafkaCheck(AgentCheck):
    """
    Check Consumer Lag for Kafka consumers that store their offsets in Zookeeper.

    WARNING: Modern Kafka consumer store their offsets in Kafka rather than
    zookeeper. You can monitor those offsets using the < TODO: TO BE NAMED > check.
    This check only monitors zookeeper-based offsets.

    This check also returns broker highwater offsets.
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

        Sends one OffsetRequest per broker to get offsets for all partitions
        where that broker is the leader:
        https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetAPI(AKAListOffset)
        """
        # We could switch this to a long-lived connection that's cached
        # on the AgentCheck instance, in which case we don't have to
        # cleanup the connection. Downside is there's no way to cleanup
        # connection when agent restarts, so brokers before 0.9 just
        # accumulate stale connections. In 0.9 Kafka added
        # connections.max.idle.ms https://issues.apache.org/jira/browse/KAFKA-1282
        kafka_client = KafkaClient(
            bootstrap_servers=kafka_hosts_ports,
            request_timeout_ms=(self.kafka_timeout * 1000))
        try:
            highwater_offsets = {}
            # store partitions that exist but unable to fetch offsets for later
            # error checking
            topic_partitions_without_a_leader = []  # contains (topic, partition) tuples
            for broker in kafka_client.cluster.brokers():
                if not kafka_client.ready(broker.nodeId):
                    time.sleep(0.5)
                if not kafka_client.ready(broker.nodeId):
                    continue

                # Group partitions by topic in order to construct the OffsetRequest
                partitions_grouped_by_topic = defaultdict(list)
                # partitions_for_broker returns all partitions for which this
                # broker is leader. So any partitions that don't currently have
                # leaders will be missed. Ignore as they'll be caught on next check run.
                for topic, partition in kafka_client.cluster.partitions_for_broker(broker.nodeId):
                    partitions_grouped_by_topic[topic].append(partition)

                # Construct the OffsetRequest
                timestamp = -1  # -1 for latest, -2 for earliest
                max_offsets = 1
                highwater_offsets_request = OffsetRequest[0](
                    replica_id=-1,
                    topics=[
                        (topic, [
                            (partition, timestamp, max_offsets) for partition in partitions])
                        for topic, partitions in partitions_grouped_by_topic.iteritems()])

                # Send each request as a blocking call to keep life simple.
                # For large clusters, be faster to send all requests and then in a
                # in a second loop process all responses. But requires bookeeping to
                # make sure all returned.
                future = kafka_client.send(broker.nodeId, highwater_offsets_request)
                kafka_client.poll(future=future)
                assert future.succeeded()  # safety net, typically only false if request was malformed.

                highwater_offsets_response = future.value
                for topic, partitions in highwater_offsets_response.topics:
                    for partition, error_code, offsets in partitions:
                        if error_code == 0:
                            highwater_offsets[(topic, partition)] = offsets[0]
                        # Valid error codes:
                        # https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-PossibleErrorCodes.2
                        elif error_code == -1:
                            self.log.error("Kafka broker returned UNKNOWN "
                                "(error_code -1) for topic: %s, partition: %s. "
                                "This should never happen.",
                                topic, partition)
                        elif error_code == 3:
                            self.log.warn("Kafka broker returned "
                                "UNKNOWN_TOPIC_OR_PARTITION (error_code 3) for "
                                "topic: %s, partition: %s. This should only "
                                "happen if the topic is currently being deleted.",
                                topic, partition)
                        elif error_code == 6:
                            self.log.warn("Kafka broker returned "
                                "NOT_LEADER_FOR_PARTITION (error_code 6) for "
                                "topic: %s, partition: %s. This should only "
                                "happen if the broker that was the partition "
                                "leader when kafka_client.cluster last fetched "
                                "metadata is no longer the leader.",
                                topic, partition)
                            topic_partitions_without_a_leader.append((topic, partition))
        finally:
            try:
                kafka_client.close()
            except Exception:
                self.log.exception('Error cleaning up Kafka connection')
        return highwater_offsets, topic_partitions_without_a_leader

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
        zk_hosts_ports = self.read_config(instance, 'zk_connect_str')
        zk_prefix = instance.get('zk_prefix', '')

        # If monitor_unlisted_consumer_groups is True, fetch all groups stored in ZK
        if instance.get('monitor_unlisted_consumer_groups', False):
            consumer_groups = None
        else:
            consumer_groups = self.read_config(instance, 'consumer_groups',
                                               cast=self._validate_consumer_groups)

        consumer_offsets = self._get_zk_consumer_offsets(
            zk_hosts_ports, consumer_groups, zk_prefix)

        # Fetch the broker highwater offsets
        kafka_hosts_ports = self.read_config(instance, 'kafka_connect_str')
        highwater_offsets, topic_partitions_without_a_leader = self._get_highwater_offsets(kafka_hosts_ports)

        # Report the broker highwater offset
        for (topic, partition), highwater_offset in highwater_offsets.iteritems():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            self.gauge('kafka.broker_offset', highwater_offset, tags=broker_tags)

        # Report the consumer group offsets and consumer lag
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.iteritems():
            consumer_group_tags = ['topic:%s' % topic, 'partition:%s' % partition,
                'consumer_group:%s' % consumer_group]
            self.gauge('kafka.consumer_offset', consumer_offset, tags=consumer_group_tags)
            if (topic, partition) not in highwater_offsets:
                if (topic, partition) not in topic_partitions_without_a_leader:
                    self.log.warn("Consumer group: %s has offsets for topic: %s "
                        "partition: %s, but that topic partition doesn't actually "
                        "exist in the cluster.", consumer_group, topic, partition)
                continue
            consumer_lag = highwater_offsets[(topic, partition)] - consumer_offset
            if consumer_lag < 0:
                # This is a really bad scenario because new messages produced to
                # the topic are never consumed by that particular consumer
                # group. So still report the negative lag as a way of increasing
                # visibility of the error.
                title = "Consumer lag for consumer negative."
                message = "Consumer lag for consumer group: {group}, topic: {topic}, " \
                    "partition: {partition} is negative. This should never happen.".format(
                        group=consumer_group,
                        topic=topic,
                        partition=partition
                    )
                key = "{}:{}:{}".format(consumer_group, topic, partition)
                self._send_event(title, message, consumer_group_tags, 'consumer_lag', key)
                self.log.debug(message)

            self.gauge('kafka.consumer_lag', consumer_lag,
               tags=consumer_group_tags)

    # Private config validation/marshalling functions

    def _validate_consumer_groups(self, val):
        # val = {'consumer_group': {'topic': [0, 1]}}
        try:
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
        except Exception as e:
            self.log.exception(e)
            raise Exception("""The `consumer_groups` value must be a mapping of mappings, like this:
consumer_groups:
  myconsumer0: # consumer group name
    mytopic0: [0, 1] # topic_name: list of partitions
  myconsumer1:
    mytopic0: [0, 1, 2]
    mytopic1: [10, 12]
  myconsumer2:
    mytopic0:
  myconsumer3:

Note that each level of values is optional. Any omitted values will be fetched from Zookeeper.
You can omit partitions (example: myconsumer2), topics (example: myconsumer3), and even consumer_groups.
If you omit consumer_groups, you must set the flag 'monitor_unlisted_consumer_groups': True.
If a value is omitted, the parent value must still be it's expected type (typically a dict).
""")

    def _send_event(self, title, text, tags, type, aggregation_key):
        event_dict = {
            'timestamp': int(time.time()),
            'source_type_name': self.SOURCE_TYPE_NAME,
            'msg_title': title,
            'event_type': type,
            'msg_text': text,
            'tags': tags,
            'aggregation_key': aggregation_key,
        }

        self.event(event_dict)
