# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

from typing import Callable, Iterator, List

import rethinkdb

from datadog_checks.base import ConfigurationError

from ._metrics import collect_default_metrics
from ._types import Instance, Metric


class Config:
    """
    Hold instance configuration for a RethinkDB check.

    Encapsulates the validation of an `instance` dictionary while improving type information.
    """

    def __init__(self, instance):
        # type: (Instance) -> None
        host = instance.get('host', 'localhost')
        port = instance.get('port', 28015)

        if not isinstance(host, str):
            raise ConfigurationError('host must be a string (got {!r})'.format(type(host)))

        if not isinstance(port, int) or isinstance(port, bool):
            raise ConfigurationError('port must be an integer (got {!r})'.format(type(port)))

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        self.host = host  # type: str
        self.port = port  # type: int

        # NOTE: this attribute exists for encapsulation and testing purposes.
        self.metric_streams = [
            collect_default_metrics
        ]  # type: List[Callable[[rethinkdb.net.Connection], Iterator[Metric]]]

    def collect_metrics(self, conn):
        # type: (rethinkdb.net.Connection) -> Iterator[Metric]
        for stream in self.metric_streams:
            for metric in stream(conn):
                yield metric

    def __repr__(self):
        # type: () -> str
        return 'Config(host={host!r}, port={port!r})'.format(host=self.host, port=self.port)
