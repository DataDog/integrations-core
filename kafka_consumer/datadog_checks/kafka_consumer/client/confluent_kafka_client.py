# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.kafka_consumer.client.kafka_client import KafkaClient


class ConfluentKafkaClient(KafkaClient):
    def create_kafka_admin_client(self):
        raise NotImplementedError

    def get_consumer_offsets_dict(self):
        raise NotImplementedError

    def get_highwater_offsets(self):
        raise NotImplementedError

    def get_highwater_offsets_dict(self):
        raise NotImplementedError

    def reset_offsets(self):
        raise NotImplementedError

    def get_partitions_for_topic(self, topic):
        raise NotImplementedError

    def request_metadata_update(self):
        raise NotImplementedError

    def collect_broker_version(self):
        raise NotImplementedError

    def get_consumer_offsets(self):
        raise NotImplementedError

    def get_broker_offset(self):
        raise NotImplementedError
