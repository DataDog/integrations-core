# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
import time

# 3p
from kafka.client import KafkaClient
from kafka.protocol.admin import ListGroupsRequest
from kafka.protocol.commit import (GroupCoordinatorRequest,
    OffsetFetchRequest, OffsetFetchResponse)
from kafka.protocol.offset import OffsetRequest, OffsetResponse

# project
from checks import AgentCheck


class KafkaCheck(AgentCheck):
    """
    Check Consumer Lag for Kafka consumers that store their offsets in Kafka.

    WARNING: Older Kafka consumer store their offsets in Zookeeper rather than
    zookeeper. You can monitor those offsets using the kafka_consumer.py check.
    This check only monitors Kafka-based offsets.

    This check also returns broker highwater offsets.

    # TODO add note about future optimization for speed of rather than a
    # having all poll() calls block, could send/process requests in parallel
    # Have to deal with bookkeeping of knowing when the futures return.
    """

    SOURCE_TYPE_NAME = 'kafka'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)

        # TODO notes about long-lived connection, no teardown, leak connections
        # below 0.9, this is one client per check instance, etc
        # We could switch this to a long-lived conneciton that's cached
        # on the AgentCheck instance, in which case we don't have to
        # cleanup the connection. Downside is there's no way to cleanup
        # connection when agent restarts, so brokers before 0.9 just
        # accumulate stale connections. In 0.9 Kafka added
        # connections.max.idle.ms https://issues.apache.org/jira/browse/KAFKA-1282

    def _get_highwater_offsets(self, kafka_client):
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
        highwater_offsets = {}
        for broker in kafka_client.cluster.brokers():
            # Group partitions by topic in order to construct the OffsetRequest
            partitions_grouped_by_topic = defaultdict(list)
            # partitions_for_broker returns all partitions for which this
            # broker is leader. So any partitions that don't currently have
            # leaders will be missed. They should be picked up on next run.
            for topic, partition in kafka_client.cluster.partitions_for_broker(broker.nodeId):
                partitions_grouped_by_topic[topic].append(partition)

            # construct the OffsetRequest
            timestamp = -1  # -1 for latest, -2 for earliest
            # TODO commented out the OffsetRequestV1 conditional code as
            # currently unfinished
            # if kafka_client.config['api_version'] < (0, 10, 1):
            max_offsets = 1
            highwater_offsets_request = OffsetRequest[0](
                replica_id=-1,
                topics=[
                    (topic, [
                        (partition, timestamp, max_offsets) for partition in partitions])
                    for topic, partitions in partitions_grouped_by_topic.iteritems()])
            # else:
            #     broker_offset_request = OffsetRequest[1](
            #         replica_id=-1,
            #         topics=[
            #             (topic, [
            #                 (partition, timestamp)
            #             ])
            #         ])
            #     # TODO flesh this out
            #     # the difference from response_v0 is addition of timestamp
            #     # which should likely also get logged in datadog so we see how far
            #     # chronologically we're behind

            future = kafka_client.send(broker.nodeId, highwater_offsets_request)

            kafka_client.poll(future=future)  # waiting for the future makes it blocking
            assert future.succeeded()  # safety net, typically only false if request was malformed.
            highwater_offsets_response = future.value
            for topic, partitions in highwater_offsets_response.topics:
                for partition, error_code, offsets in partitions:
                    if error_code == 0:
                        # TODO not sure v2 returns offsets in a list, might be just one
                        highwater_offsets[(topic, partition)] = offsets[0]
                    # Valid error codes:
                    # https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-PossibleErrorCodes.2
                    elif error_code == -1:
                        self.log.exception("Kafka broker returned UNKNOWN "
                            "(error_code -1) for topic: %s, partition: %s. "
                            "This should never happen.",
                            topic, partition)
                    elif error_code == 3:
                        self.log.warn("Kafka broker returned "
                            "UNKNOWN_TOPIC_OR_PARTITION (error_code 3) for "
                            "topic: %s, partition: %s. This should only "
                            "happen if the topic is currently being deleted.",
                            topic, partition)
                        # TODO trigger a metadata refresh as likely multiple
                        # partitions have changed
                    elif error_code == 6:
                        self.log.warn("Kafka broker returned "
                            "NOT_LEADER_FOR_PARTITION (error_code 6) for "
                            "topic: %s, partition: %s. This should only "
                            "happen if the broker that was the partition "
                            "leader when kafka_client.cluster last fetched "
                            "metadata is no longer leader.",
                            topic, partition)
                        # TODO trigger a metadata refresh as likely multiple
                        # partitions switched leaders
                    elif error_code == 43:  # only appears for OffsetRequest_v1
                        self.log.warn("Kafka broker returned "
                            "UNSUPPORTED_FOR_MESSAGE_FORMAT (error_code 43) for"
                            " topic: %s, partition: %s. This topic has not "
                            "enabled the 0.10 message format.",
                            topic, partition)
                        # TODO need a way to pin the check to using
                        # OffsetRequest_v0 even if broker version is newer
                        # but first check if OffsetRequest_v1 actually adds value
        return highwater_offsets

    def _update_kafka_client_cluster_with_list_groups_response(self, kafka_client, broker):
        """Update cluster metadata with the list_groups_response from the given broker.

        Works by sending a ListGroupsRequest to the broker. This call is only
        supported on brokers >= 0.9 and only returns new-style consumer groups.
        Also updates the groups' GroupCoordinator because the broker that
        returns a group is also the group's coordinator.
        """
        if kafka_client.config['api_version'] < (0, 9, 0):
            # TODO raise or return
            raise ## custom message
        future = kafka_client.send(broker.nodeId, ListGroupsRequest[0]())
        kafka_client.poll(future=future)
        assert future.succeeded()  # safety net, typically only false if request was malformed.
        list_groups_response = future.value
        # TODO handle error codes GROUP_COORDINATOR_NOT_AVAILABLE
        # import pdb; pdb.set_trace()
        for group, protocol_type in list_groups_response.groups:
            if protocol_type == 'consumer':
                kafka_client.cluster._groups[group] = broker.nodeId
        # import pdb; pdb.set_trace()

    def _update_kafka_client_cluster_group_coordinator(self, kafka_client, group):
        """Updates the Cluster metadata with the group coordinator for the given group."""
        group_coordinator_request = GroupCoordinatorRequest[0](group)
        # send requests to the least loaded node:
        broker_id = kafka_client.least_loaded_node()
        future = kafka_client.send(broker_id, group_coordinator_request)
        kafka_client.poll(future=future)
        assert future.succeeded()  # safety net, typically only false if request was malformed.
        group_coordinator_response = future.value
        # use this built-in method to parse response because has built-in error handling
        # it's an error if it returns False.
        # TODO we need to check if error is unknown group, then, if also uknown in manual YAML list, then delete from _groups.
        # TODO Also return an error so that a caller can know to bail out of further processing that group
        kafka_client.cluster.add_group_coordinator(group, group_coordinator_response)


    def _fetch_offsets_for_consumer_group(self, kafka_client, group, topics=None):
        """
        Fetches offsets for all partitions because most consumer groups will
        be fetch offsets for all partitions.

            :param: topics Should be a list.
            # TODO add comment that topics only used (and required) for brokers < 0.10.2.
            # And done this way not because it's intuitive, but because no easy way
            # to see which topics a group is consuming otherwise.
        """
        if kafka_client.cluster.coordinator_for_group(group) is None:
            self._update_kafka_client_cluster_group_coordinator(kafka_client, group)
            # TODO bail out at this point if group doesn't exist in the cluster

        valid_topics = set()
        for topic in topics:
            if topic in kafka_client.cluster.topics():
                valid_topics.add(topic)
            else:
                self.log.warn("Requested offsets for consumer group %s, "
                    "topic %s but that topic doesn't exist in the cluster.",
                    group, topic)

        if kafka_client.config['api_version'] < (0, 10, 2):
            if topics is None:
                raise  # TODO custom error message about topics required because no easy way
                # to see which topics a group is consuming otherwise
            consumer_offsets_request = OffsetFetchRequest[1](group, [(topic, kafka_client.cluster.partitions_for_topic(topic)) for topic in valid_topics])
        else:
            consumer_offsets_request = OffsetFetchRequest[2](group)
        coordinator_id = kafka_client.cluster.coordinator_for_group(group)
        future = kafka_client.send(coordinator_id, consumer_offsets_request)
        kafka_client.poll(future=future)
        if future.succeeded() is False:
            # import pdb; pdb.set_trace()
            pass
        assert future.succeeded()  # safety net, typically only false if request was malformed.
        consumer_offsets_response = future.value
        group_offsets = {}
        if isinstance(consumer_offsets_response, OffsetFetchResponse[1]):
            for topic, partitions in consumer_offsets_response.topics:
                for partition, offset, metadata, error_code in partitions:
                    if error_code == 0:
                        if offset != -1:
                            # skip because offset of -1 means no stored offset
                            # for this consumer group / topic_partition combo
                            group_offsets[(group, topic, partition)] = offset
                    else:
                        # import pdb; pdb.set_trace()
                        pass
                        # TODO handle error codes
                        # * GROUP_LOAD_IN_PROGRESS (14)
                        # * NOT_COORDINATOR_FOR_GROUP (16)
                        # * ILLEGAL_GENERATION (22)
                        # * UNKNOWN_MEMBER_ID (25)
                        # * TOPIC_AUTHORIZATION_FAILED (29)
                        # * GROUP_AUTHORIZATION_FAILED (30)
                        # TODO since kafka always uses unique error codes for all protocol calls, then have a separate error handling function:
                        # https://kafka.apache.org/protocol.html#protocol_error_codes
        elif isinstance(consumer_offsets_response, OffsetFetchResponse[2]):
            pass  # not implemented yet
            # TODO handle error codes - v2 added top-level error codes
        # caller saves offsets as consumer_offsets[(group, topic, partition)] = offset
        return group_offsets

    def check(self, instance):
        kafka_hosts_ports = self.read_config(instance, 'kafka_connect_str')
        kafka_client = KafkaClient(bootstrap_servers=kafka_hosts_ports)
        # Make sure we've got valid connections to all the brokers in the cluster
        for broker in kafka_client.cluster.brokers():
            if not kafka_client.ready(broker.nodeId):
                time.sleep(0.5)
            if not kafka_client.ready(broker.nodeId):
                raise ## custom error message about broker not ready

        # Make sure yaml-specified groups are in cluster metadata
        if instance.get('consumer_groups') is not None:
            yaml_consumer_groups = self.read_config(instance, 'consumer_groups',
                                               cast=self._validate_consumer_groups)
            for group in yaml_consumer_groups:
                # Default is None since coordinator_id is unknown at this point
                kafka_client.cluster._groups.setdefault(group)

        # While ListGroupsRequest was added in 0.9, it's very difficult to
        # figure out the topics the group is consuming, so only support this
        # if the broker also supports KIP-88 (0.10.2 or greater)
        if instance.get('monitor_unlisted_consumer_groups', False) is True and \
            kafka_client.config['api_version'] >= (0, 10, 2):
            for broker in kafka_client.cluster.brokers():
                self._update_kafka_client_cluster_with_list_groups_response(kafka_client, broker)
            # TODO if caching metadata on the instance, then it's tricky to
            # combine dynamically fetch groups with the yaml-specified groups
            # into cluster._groups because want to keep fetching yaml ones...
            # if a broker throws "group unknown", then only delete from
            # cluster._groups when not in the yaml list. As a safety check, we also re-populate the YAML each time

        # Fetch offsets:
        # For calculating lag, we have to fetch both highwater broker offsets
        # and consumer offsets. There's a potential race condition because
        # whichever one we check first may be outdated by the time we check the
        # other. Better to check consumer offset before checking broker offset
        # because worst case is that overstates consumer lag a little. Doing it
        # the other way can understate consumer lag to the point of having
        # negative consumer lag, which just creates confusion because it's
        # theoretically impossible.

        # Optimization: Could use a while loop to send/receive offset requests
        # in a non-blocking fashion.
        consumer_offsets = {}  # consumer_offsets[(group, topic, partition)] = offset
        for group in kafka_client.cluster._groups:
            topics = yaml_consumer_groups.get(group)  # TODO this means even in broker > 0.10.2 if topics are specified, only they will be fetched.
            group_offsets = self._fetch_offsets_for_consumer_group(
                kafka_client, group, topics=topics)
            consumer_offsets.update(group_offsets)

        # Fetch the broker highwater offsets
        highwater_offsets = self._get_highwater_offsets(kafka_client)

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
                # TODO add the logic from kafka_consumer.py for when partition exists but no leader
                self.log.exception("Consumer offsets exist for topic: {topic} "
                    "partition: {partition} but that topic partition doesn't "
                    "actually exist in the cluster.".format(**locals()))
                continue
            consumer_lag = highwater_offsets[(topic, partition)] - consumer_offset
            if consumer_lag < 0:
                # This is a really bad scenario because new messages produced to
                # the topic are never consumed by that particular consumer
                # group. So still report the negative lag as a way of increasing
                # visibility of the error.
                # TODO is this already protected against in Kafka? check
                self.log.exception("Consumer lag for consumer group: "
                    "{consumer_group}, topic: {topic}, partition: {partition} "
                    "is negative. This should never happen.".format(**locals()))
            # TODO should we even be storing this? We could calculate it
            # dynamically in datadog by creating a graph that does the subtraction
            # Basically trades storage space for CPU within Datadog so up to them.
            self.gauge('kafka.consumer_lag', consumer_lag,
               tags=consumer_group_tags)

        # TODO wrap this in try/except/finally blocks
        kafka_client.close()

    # Private config validation/marshalling functions

    def _validate_consumer_groups(self, val):
        # TODO add conditional validation based on kafka_client.config['api_version']
        # if broker < 0.10.2, must specify consumer groups and topics
        # val = {'consumer_group': ['topic']}
        try:
            # consumer groups are optional
            assert isinstance(val, dict) or val is None
            if isinstance(val, dict):
                for consumer_group, topics in val.iteritems():
                    assert isinstance(consumer_group, (str, unicode))
                    # topics are optional
                    assert isinstance(topics, list) or topics is None
                    if isinstance(topics, list):
                        for topic in topics:
                            assert isinstance(topic, (str, unicode))
            return val
        except Exception as e:
            self.log.exception(e)
            raise Exception("""TODO For Kafka clusters < 0.10.2, the `consumer_groups` value must list both consumer group names and the topics they are subscribed to:
consumer_groups:
  my_consumer_0: # consumer group name
    - my_topic_0 # topic name
    - my_topic_1

For Kafka clusters >= 0.10.2, the `consumer_groups` value only needs to list the consumer groups. Offsets will be fetched for all topics to which the consumer group is subscribed:
consumer_groups:
  my_consumer_1
  my_consumer_2
# TODO add a note about monitor_unlisted_consumer_groups
  """)
