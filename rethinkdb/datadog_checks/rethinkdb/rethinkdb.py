# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Required for `import rethinkdb` to correctly import the client package (instead of this package) on Python 2.
from __future__ import absolute_import

from contextlib import contextmanager
from typing import Any, Callable, Iterator

import rethinkdb

from datadog_checks.base import AgentCheck

from ._config import Config
from ._types import ConnectionServer, Instance, Metric

SERVICE_CHECK_CONNECT = 'rethinkdb.can_connect'


class RethinkDBCheck(AgentCheck):
    """
    Collect metrics from a RethinkDB cluster.

    A set of default metrics is collected from system tables.
    """

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(RethinkDBCheck, self).__init__(*args, **kwargs)
        self.config = Config(self.instance)

    @contextmanager
    def connect_submitting_service_checks(self, config):
        # type: (Config) -> Iterator[rethinkdb.net.Connection]
        try:
            with config.connect() as conn:
                server = conn.server()  # type: ConnectionServer
                self.log.debug('connected server=%r', server)
                tags = ['server:{}'.format(server['name'])]

                try:
                    yield conn
                except Exception as exc:
                    message = 'Unexpected error while executing RethinkDB check: {!r}'.format(exc)
                    self.log.error(message)
                    self.service_check(SERVICE_CHECK_CONNECT, self.CRITICAL, tags=tags, message=message)
                    raise
                else:
                    self.service_check(SERVICE_CHECK_CONNECT, self.OK, tags=tags)

        except rethinkdb.errors.ReqlDriverError as exc:
            message = 'Could not connect to RethinkDB server: {!r}'.format(exc)
            self.log.error(message)
            self.service_check(SERVICE_CHECK_CONNECT, self.CRITICAL, message=message)
            raise

    def submit_metric(self, metric):
        # type: (Metric) -> None
        self.log.debug('submit_metric metric=%r', metric)
        if metric['type'] == 'service_check':
            self.service_check(metric['name'], metric['value'], tags=metric['tags'])
        else:
            submit = getattr(self, metric['type'])  # type: Callable
            submit(metric['name'], value=metric['value'], tags=metric['tags'])

    def check(self, instance):
        # type: (Instance) -> None
        config = self.config
        self.log.debug('check config=%r', config)

        with self.connect_submitting_service_checks(config) as conn:
            for metric in config.collect_metrics(conn):
                self.submit_metric(metric)

            version = config.get_connected_server_version(conn)
            self.set_metadata('version', version)
