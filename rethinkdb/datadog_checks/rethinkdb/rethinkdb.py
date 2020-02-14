# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Required for `import rethinkdb` to correctly import the client package (instead of this package) on Python 2.
from __future__ import absolute_import

from contextlib import contextmanager
from typing import Any, Callable, Iterator, List

import rethinkdb

from datadog_checks.base import AgentCheck

from ._config import Config
from ._default_metrics import collect_default_metrics
from ._types import ConnectionServer, Instance, Metric


class RethinkDBCheck(AgentCheck):
    """
    Collect metrics from a RethinkDB cluster.

    A set of default metrics is collected from system tables.
    """

    # NOTE: use of private names (double underscores, e.g. '__member') prevents name clashes with the base class.

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(RethinkDBCheck, self).__init__(*args, **kwargs)

        self.__config = Config(self.instance)

        # NOTE: this list is exposed for testing purposes.
        self._metric_collectors = []  # type: List[Callable[[rethinkdb.net.Connection], Iterator[Metric]]]
        self._metric_collectors.append(collect_default_metrics)

    def check(self, instance):
        # type: (Instance) -> None
        config = self.__config
        self.log.debug('check config=%r', config)

        host = config.host
        port = config.port

        with self.__submit_service_check() as on_connection_established:
            with rethinkdb.r.connect(db='rethinkdb', host=host, port=port) as conn:
                on_connection_established(conn)
                for metric in self.__collect_metrics(conn):
                    self.__submit_metric(metric)

    def __collect_metrics(self, conn):
        # type: (rethinkdb.net.Connection) -> Iterator[Metric]
        for collect in self._metric_collectors:
            for metric in collect(conn):
                yield metric

    @contextmanager
    def __submit_service_check(self):
        # type: () -> Iterator[Callable[[rethinkdb.net.Connection], None]]
        tags = []  # type: List[str]

        def on_connection_established(conn):
            # type: (rethinkdb.net.Connection) -> None
            server = conn.server()  # type: ConnectionServer
            self.log.debug('connected server=%r', server)
            tags.append('server:{}'.format(server['name']))
            # TODO: add a 'proxy' tag if server is a proxy?

        try:
            yield on_connection_established
        except rethinkdb.errors.ReqlDriverError as exc:
            self.log.error('Could not connect to RethinkDB server: %r', exc)
            self.service_check('rethinkdb.can_connect', self.CRITICAL, tags=tags)
        except Exception as exc:
            self.log.error('Unexpected error while executing RethinkDB check: %r', exc)
            self.service_check('rethinkdb.can_connect', self.CRITICAL, tags=tags)
        else:
            self.log.debug('service_check OK')
            self.service_check('rethinkdb.can_connect', self.OK, tags=tags)

    def __submit_metric(self, metric):
        # type: (Metric) -> None
        self.log.debug('submit_metric metric=%r', metric)
        submit = getattr(self, metric['type'])  # type: Callable
        submit(metric['name'], value=metric['value'], tags=metric['tags'])

    # TODO: version metadata.
    # TODO: custom queries. (Hint: look at `QueryManager`.)
    # TODO: allow not sending default metrics.
    # TODO: decide if and how to deal with `identifier_format`: https://rethinkdb.com/api/python/table/#description
