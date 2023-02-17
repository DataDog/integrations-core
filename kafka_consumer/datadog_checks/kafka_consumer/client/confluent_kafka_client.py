# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from confluent_kafka.admin import AdminClient
from confluent_kafka import Consumer, TopicPartition

EXCLUDED_TOPICS = ['__consumer_offsets', '__transaction_state']

class ConfluentKafkaClient:
    def __init__(self, config, tls_context, log) -> None:
        self.config = config
        self.log = log
        self._kafka_client = None
        self._highwater_offsets = {}
        self._consumer_offsets = {}
        self._tls_context = tls_context
    
    @property
    def kafka_client(self):
        if self._kafka_client is None:
            # self.conf is just the config options from librdkafka
            self._kafka_client = AdminClient(self.conf)

        return self._kafka_client

    def get_highwater_offsets(self):
        # {(topic, partition): offset}
        for consumer_group in self.config._consumer_groups:
            config = {
                "bootstrap.servers" : self.config._kafka_connect_str,
                "group.id": consumer_group,
            }
            consumer = Consumer(config)

            # TODO: AdminClient also has a list_topics(), see if Consumer.list_topics() is the same
            topics = consumer.list_topics()

            for topic in topics.topics:
                # TODO: See if there's an internal function to automatically exclude internal topics
                if topic not in EXCLUDED_TOPICS:
                    topic_partitions = [
                        TopicPartition(topic, partition) for partition in list(topics.topics[topic].partitions.keys())
                    ]

                    for topic_partition in topic_partitions:
                        _, high_offset = consumer.get_watermark_offsets(topic_partition)

                        self._highwater_offsets[(topic, topic_partition.partition)] = high_offset
    

    def get_consumer_offsets(self):
        # {(consumer_group, topic, partition): offset}
        # client.list_consumer_group_offsets(list_consumer_group_offsets_request)
        # ConsumerGroupTopicPartitions object
        pass

    def get_consumer_offsets_dict(self):
        return {}

    def get_highwater_offsets_dict(self):
        self.log.error(self._highwater_offsets)
        return self._highwater_offsets

    def get_partitions_for_topic(self):
        pass

    def request_metadata_update(self):
        # May not need this
        pass

    def collect_broker_version(self):
        pass

    def reset_offsets(self):
        self._consumer_offsets = {}
        self._highwater_offsets = {}
