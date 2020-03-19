# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from typing import Any, Callable, Iterator, cast

from datadog_checks.base import AgentCheck

from .backends import Backend
from .config import Config
from .connections import Connection
from .exceptions import CouldNotConnect, VersionCollectionFailed
from .types import Instance, Metric

SERVICE_CHECK_CONNECT = 'rethinkdb.can_connect'


class RethinkDBCheck(AgentCheck):
    """
    Collect metrics from a RethinkDB cluster.
    """

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(RethinkDBCheck, self).__init__(*args, **kwargs)
        self.config = Config(cast(Instance, self.instance))
        self.backend = Backend()

    @contextmanager
    def connect_submitting_service_checks(self):
        # type: () -> Iterator[Connection]
        tags = [
            'host:{}'.format(self.config.host),
            'port:{}'.format(self.config.port),
        ]
        tags.extend(self.config.tags)

        try:
            with self.backend.connect(self.config) as conn:
                yield conn
        except CouldNotConnect as exc:
            message = 'Could not connect to RethinkDB server: {!r}'.format(exc)
            self.log.error(message)
            self.service_check(SERVICE_CHECK_CONNECT, self.CRITICAL, tags=tags, message=message)
            raise
        except Exception as exc:
            message = 'Unexpected error while executing RethinkDB check: {!r}'.format(exc)
            self.log.exception(message)
            self.service_check(SERVICE_CHECK_CONNECT, self.CRITICAL, tags=tags, message=message)
            raise
        else:
            self.service_check(SERVICE_CHECK_CONNECT, self.OK, tags=tags)

    def submit_metric(self, metric):
        # type: (Metric) -> None
        metric_type = metric['type']
        name = metric['name']
        value = metric['value']
        tags = self.config.tags + metric['tags']

        self.log.debug('submit_metric type=%r name=%r value=%r tags=%r', metric_type, name, value, tags)

        submit = getattr(self, metric_type)  # type: Callable
        submit(name, value, tags=tags)

    def submit_version_metadata(self, conn):
        # type: (Connection) -> None
        try:
            version = self.backend.collect_connected_server_version(conn)
        except VersionCollectionFailed as exc:
            self.log.error(exc)
        else:
            self.set_metadata('version', version)

    def check(self, instance):
        # type: (Any) -> None
        self.log.debug('check config=%r', self.config)

        with self.connect_submitting_service_checks() as conn:
            for metric in self.backend.collect_metrics(conn):
                self.submit_metric(metric)

            if self.is_metadata_collection_enabled():
                self.submit_version_metadata(conn)
