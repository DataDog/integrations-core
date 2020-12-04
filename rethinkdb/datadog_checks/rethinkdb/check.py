# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from typing import Any, Callable, Iterator, List, Optional, cast

import rethinkdb

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from . import queries
from .config import Config
from .types import Instance


class RethinkDBCheck(AgentCheck):
    """
    Collect metrics from a RethinkDB cluster.
    """

    __NAMESPACE__ = 'rethinkdb'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(RethinkDBCheck, self).__init__(*args, **kwargs)

        self.config = Config(cast(Instance, self.instance))

        if self.config.password:
            self.register_secret(self.config.password)

        self._conn = None  # type: Optional[rethinkdb.net.Connection]

        manager_queries = [
            queries.ClusterMetrics,
            queries.ServerMetrics,
            queries.DatabaseMetrics,
            queries.DatabaseTableMetrics,
            queries.TableMetrics,
            queries.ReplicaMetrics,
            queries.ShardMetrics,
            queries.JobMetrics,
            queries.CurrentIssuesMetrics,
        ]  # type: list

        if self.is_metadata_collection_enabled:
            manager_queries.append(queries.VersionMetadata)

        self._query_manager = QueryManager(
            self,
            executor=self._execute_raw_query,
            queries=manager_queries,
            tags=self.config.tags,
        )

        self.check_initializations.append(self._query_manager.compile_queries)

    def _execute_raw_query(self, query):
        # type: (Callable[[rethinkdb.net.Connection], List[tuple]]) -> List[tuple]
        query_func = query
        return query_func(self._conn)

    @contextmanager
    def connect_submitting_service_checks(self):
        # type: () -> Iterator[None]
        config = self.config
        tags = config.service_check_tags

        try:
            with rethinkdb.r.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                ssl={'ca_certs': config.tls_ca_cert} if config.tls_ca_cert is not None else {},
            ) as conn:
                self._conn = conn
                yield
        except rethinkdb.errors.ReqlDriverError as exc:
            message = 'Could not connect to RethinkDB server: {!r}'.format(exc)
            self.log.error(message)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=tags, message=message)
            raise
        except Exception as exc:
            message = 'Unexpected error while executing RethinkDB check: {!r}'.format(exc)
            self.log.error(message)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=tags, message=message)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=tags)
        finally:
            self._conn = None

    def collect_metrics(self):  # Exposed for mocking purposes.
        # type: () -> None
        self._query_manager.execute()

    def check(self, instance):
        # type: (Any) -> None
        with self.connect_submitting_service_checks():
            self.collect_metrics()
