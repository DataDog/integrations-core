# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class ConfluentKafkaClient:
    def __init__(self) -> None:
        # self.client ?
        # self.consumer ?
        pass

    def get_consumer_offsets_dict(self):
        # {(consumer_group, topic, partition): offset}
        # list_consumer_group_offsets(list_consumer_group_offsets_request)
        # ConsumerGroupTopicPartitions object
        pass

    def get_highwater_offsets_dict(self):
        # {(topic, partition): offset}
        # consumer.get_watermark_offsets()
        # TopicPartition object
        pass

    def get_partitions_for_topic(self):
        pass

    def request_metadata_update(self):
        # May not need this
        pass

    def collect_broker_version(self):
        pass

    def reset_offsets(self):
        pass
    