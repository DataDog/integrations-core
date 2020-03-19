# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Sequence, cast

import rethinkdb

from datadog_checks.base import AgentCheck

from . import operations
from .config import Config
from .metrics.config import collect_config_totals
from .metrics.current_issues import collect_current_issues
from .metrics.statistics import (
    collect_cluster_statistics,
    collect_replica_statistics,
    collect_server_statistics,
    collect_table_statistics,
)
from .metrics.statuses import collect_server_status, collect_table_status
from .metrics.system_jobs import collect_system_jobs
from .types import Instance, Metric
from .version import parse_version

SERVICE_CHECK_CONNECT = 'rethinkdb.can_connect'


class RethinkDBCheck(AgentCheck):
    """
    Collect metrics from a RethinkDB cluster.
    """

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(RethinkDBCheck, self).__init__(*args, **kwargs)
        self.config = Config(cast(Instance, self.instance))
        self.collect_funcs = (
            collect_config_totals,
            collect_cluster_statistics,
            collect_server_statistics,
            collect_table_statistics,
            collect_replica_statistics,
            collect_server_status,
            collect_table_status,
            collect_system_jobs,
            collect_current_issues,
        )  # type: Sequence[Callable]

    @contextmanager
    def connect_submitting_service_checks(self):
        # type: () -> Iterator[rethinkdb.net.Connection]
        config = self.config

        tags = ['host:{}'.format(config.host), 'port:{}'.format(config.port)]
        tags.extend(config.tags)

        try:
            with rethinkdb.r.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                ssl={'ca_certs': config.tls_ca_cert} if config.tls_ca_cert is not None else None,
            ) as conn:
                yield conn
        except rethinkdb.errors.ReqlDriverError as exc:
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

    def collect_metrics(self, conn):
        # type: (rethinkdb.net.Connection) -> Iterator[Metric]
        """
        Collect metrics from the RethinkDB cluster we are connected to.
        """
        for collect in self.collect_funcs:
            for metric in collect(conn):
                yield metric

    def collect_connected_server_version(self, conn):
        # type: (rethinkdb.net.Connection) -> str
        """
        Return the version of RethinkDB run by the server at the other end of the connection, in SemVer format.
        """
        version_string = operations.query_connected_server_version_string(conn)
        return parse_version(version_string)

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
        # type: (rethinkdb.net.Connection) -> None
        try:
            version = self.collect_connected_server_version(conn)
        except ValueError as exc:
            self.log.error(exc)
        else:
            self.set_metadata('version', version)

    def check(self, instance):
        # type: (Any) -> None
        self.log.debug('check config=%r', self.config)

        with self.connect_submitting_service_checks() as conn:
            for metric in self.collect_metrics(conn):
                self.submit_metric(metric)

            if self.is_metadata_collection_enabled():
                self.submit_version_metadata(conn)
