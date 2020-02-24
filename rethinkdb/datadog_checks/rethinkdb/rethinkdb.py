# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Required for `import rethinkdb` to correctly import the client package (instead of this package) on Python 2.
from __future__ import absolute_import

from contextlib import contextmanager
from typing import Any, Callable, Iterator, List

import rethinkdb
from rethinkdb import r

from datadog_checks.base import AgentCheck

from ._config import Config
from ._types import ConnectionServer, Instance, Metric


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
    def connect_submitting_service_check(self, host, port):
        # type: (str, int) -> Iterator[rethinkdb.net.Connection]
        tags = []  # type: List[str]

        try:
            with r.connect(host=host, port=port) as conn:
                server = conn.server()  # type: ConnectionServer
                self.log.debug('connected server=%r', server)
                tags.append('server:{}'.format(server['name']))
                yield conn
        except rethinkdb.errors.ReqlDriverError as exc:
            self.log.error('Could not connect to RethinkDB server: %r', exc)
            self.service_check('rethinkdb.can_connect', self.CRITICAL, tags=tags)
            raise
        except Exception as exc:
            self.log.error('Unexpected error while executing RethinkDB check: %r', exc)
            self.service_check('rethinkdb.can_connect', self.CRITICAL, tags=tags)
            raise
        else:
            self.log.debug('service_check OK')
            self.service_check('rethinkdb.can_connect', self.OK, tags=tags)

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

        host = config.host
        port = config.port

        with self.connect_submitting_service_check(host, port) as conn:
            for metric in config.collect_metrics(conn):
                self.submit_metric(metric)

    # TODO: version metadata.
    # TODO: custom queries. (Hint: look at `QueryManager`.)
    # TODO: allow not sending default metrics.
    # TODO: decide if and how to deal with `identifier_format`: https://rethinkdb.com/api/python/table/#description
