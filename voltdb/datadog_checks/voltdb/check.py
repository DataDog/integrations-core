# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Any, List, cast

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from . import _queries as queries
from ._config import Config
from ._types import Instance


class VoltDBCheck(AgentCheck):
    __NAMESPACE__ = 'voltdb'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(VoltDBCheck, self).__init__(*args, **kwargs)
        self._config = Config(cast(Instance, self.instance))

        if self._config.auth is not None:
            _, password = self._config.auth
            self.register_secret(password)

        self._query_manager = QueryManager(
            self,
            self._execute_query_raw,
            queries=[
                queries.CPUMetrics,
                queries.MemoryMetrics,
                queries.SnapshotStatusMetrics,
                queries.CommandLogMetrics,
                queries.ProcedureMetrics,
                queries.LatencyMetrics,
                queries.StatementMetrics,
                queries.GCMetrics,
                queries.IOStatsMetrics,
                queries.TableMetrics,
                queries.IndexMetrics,
            ],
            tags=self._config.tags,
        )
        self.check_initializations.append(self._query_manager.compile_queries)

    def _execute_query_raw(self, query):
        # type: (str) -> List[tuple]
        component = query
        params = self._config.build_api_params(procedure='@Statistics', parameters=[component])
        # auth=None: prevent RequestsWrapper from using username/password as basic auth.
        response = self.http.get(self._config.api_url, params=params, auth=None)
        response.raise_for_status()
        raw = response.json()
        results = raw['results'][0]
        return results['data']

    def _check_can_connect(self):
        params = self._config.build_api_params(procedure='@SystemInformation')

        try:
            # auth=None: prevent RequestsWrapper from using username/password as basic auth.
            r = self.http.get(self._config.api_url, params=params, auth=None)
        except Exception as exc:
            message = 'Unable to connect to VoltDB: {}'.format(exc)
            self.service_check('can_connect', self.CRITICAL, message=message, tags=self._config.tags)
            raise

        try:
            r.raise_for_status()
        except Exception as exc:
            message = 'Error response from VoltDB: {}'.format(exc)
            try:
                details = r.json()["statusstring"]
            except (json.JSONDecodeError, KeyError):
                pass
            else:
                message += ' (details: {})'.format(details)
            self.service_check('can_connect', self.CRITICAL, message=message, tags=self._config.tags)
            raise

        self.service_check('can_connect', self.OK, tags=self._config.tags)

    def check(self, _):
        # type: (Any) -> None
        self._check_can_connect()
        self._query_manager.execute()
