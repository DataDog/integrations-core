# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from abc import ABC, abstractmethod


class KafkaClient(ABC):
    def __init__(self, check) -> None:
        self.check = check
        self.log = check.log
        self._kafka_client = None
        self._highwater_offsets = {}
        self._consumer_offsets = {}
        self._context_limit = check._context_limit

    def should_get_highwater_offsets(self):
        return len(self._consumer_offsets) < self._context_limit

    @abstractmethod
    def get_consumer_offsets(self):
        pass

    @abstractmethod
    def get_highwater_offsets(self):
        pass

    @abstractmethod
    def collect_broker_metadata(self):
        pass
