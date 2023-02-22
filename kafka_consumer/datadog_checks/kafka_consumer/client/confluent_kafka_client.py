# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class ConfluentKafkaClient:
    def __init__(self, config, tls_context, log) -> None:
        self.config = config
        self.log = log
        self._tls_context = tls_context

    def get_consumer_offsets(self):
        pass

    def get_broker_offset(self):
        pass
