# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Required for `import rethinkdb` to correctly import the client package (instead of this package) on Python 2.
from __future__ import absolute_import

from contextlib import contextmanager
from typing import Any, Callable, Iterator, List

from datadog_checks.base import AgentCheck

from ._config import Config
from ._connections import Connection
from ._exceptions import CouldNotConnect, VersionCollectionFailed
from ._types import Instance, Metric

SERVICE_CHECK_CONNECT = 'rethinkdb.can_connect'


class RethinkDBCheck(AgentCheck):
    """
    Collect metrics from a RethinkDB cluster.
    """

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(RethinkDBCheck, self).__init__(*args, **kwargs)
        self.config = Config(self.instance)

    @contextmanager
    def connect_submitting_service_checks(self, config):
        # type: (Config) -> Iterator[Connection]
        tags = []  # type: List[str]

        try:
            with config.connect() as conn:
                server = conn.server()

                connection_tags = [
                    'host:{}'.format(conn.host),
                    'port:{}'.format(conn.port),
                    'server:{}'.format(server['name']),
                    'proxy:{}'.format('true' if server['proxy'] else 'false'),
                ]

                self.log.debug('connected connection_tags=%r', connection_tags)
                tags.extend(connection_tags)

                yield conn

        except CouldNotConnect as exc:
            message = 'Could not connect to RethinkDB server: {!r}'.format(exc)
            self.log.error(message)
            self.service_check(SERVICE_CHECK_CONNECT, self.CRITICAL, tags=tags, message=message)
            raise
        except Exception as exc:
            message = 'Unexpected error while executing RethinkDB check: {!r}'.format(exc)
            self.log.error(message)
            self.service_check(SERVICE_CHECK_CONNECT, self.CRITICAL, tags=tags, message=message)
            raise
        else:
            self.service_check(SERVICE_CHECK_CONNECT, self.OK, tags=tags)

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

            try:
                version = config.collect_connected_server_version(conn)
            except VersionCollectionFailed as exc:
                self.log.error(exc)
            else:
                self.set_metadata('version', version)
