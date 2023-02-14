# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from abc import ABC, abstractmethod


class KafkaClient(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def get_consumer_offsets(self):
        pass

    @abstractmethod
    def get_highwater_offsets(self):
        pass

    @abstractmethod
    def get_version(self):
        pass

    @abstractmethod
    def get_partitions_for_topic(self, topic):
        pass

    @abstractmethod
    def request_update(self):
        pass
