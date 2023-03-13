# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from abc import ABC, abstractmethod


class KafkaClient(ABC):
    def __init__(self, config, tls_context, log) -> None:
        self.config = config
        self.log = log
        self._kafka_client = None
        self._highwater_offsets = {}
        self._consumer_offsets = {}
        self._tls_context = tls_context

    @abstractmethod
    def get_consumer_offsets(self):
        pass

    @abstractmethod
    def get_consumer_offsets_dict(self):
        pass

    @abstractmethod
    def get_highwater_offsets(self):
        pass

    @abstractmethod
    def get_highwater_offsets_dict(self):
        pass

    @abstractmethod
    def reset_offsets(self):
        pass

    @abstractmethod
    def get_partitions_for_topic(self, topic):
        pass

    @abstractmethod
    def request_metadata_update(self):
        pass
