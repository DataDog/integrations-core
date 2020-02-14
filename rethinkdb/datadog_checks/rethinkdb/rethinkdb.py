# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Required for `import rethinkdb` to correctly import the client package (instead of this package) on Python 2.
from __future__ import absolute_import

from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List

import rethinkdb

from datadog_checks.base import AgentCheck

from ._config import Config
from ._default_metrics import collect_default_metrics
from ._types import ConnectionServer, Metric


class RethinkDBCheck(AgentCheck):
    """
    Collect metrics from a RethinkDB cluster.

    A set of default metrics is collected from system tables.
    """

    # NOTE: use of private names (double underscores, e.g. '__member') prevents name clashes with the base class.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__config = Config(self.instance)  # type: Config  # (Mypy is confused without this hint... :wtf:)

    def check(self, instance):
        # type: (Dict[str, Any]) -> None
        self.log.debug('check config=%r', self.__config)

        host = self.__config.host
        port = self.__config.port

        with self.__submit_service_check() as on_connection_established:
            with rethinkdb.r.connect(db='rethinkdb', host=host, port=port) as conn:
                on_connection_established(conn)
                for metric in collect_default_metrics(conn):
                    self.__submit_metric(metric)

    @contextmanager
    def __submit_service_check(self):
        # type: () -> Iterator[Callable[[rethinkdb.net.Connection], None]]
        tags = []  # type: List[str]

        def on_connection_established(conn):
            # type: (rethinkdb.net.Connection) -> None
            server = conn.server()  # type: ConnectionServer
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
            self.service_check('rethinkdb.can_connect', self.OK, tags=tags)

    def __submit_metric(self, metric):
        # type: (Metric) -> None
        submit = getattr(self, metric['type'])  # type: Callable
        submit(metric['name'], value=metric['value'], tags=metric['tags'])

    # TODO: version metadata.
    # TODO: custom queries. (Hint: look at `QueryManager`.)
    # TODO: allow not sending default metrics.
    # TODO: decide if and how to deal with `identifier_format`: https://rethinkdb.com/api/python/table/#description
