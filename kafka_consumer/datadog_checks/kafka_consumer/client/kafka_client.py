# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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
