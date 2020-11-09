# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Any, List, cast

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager, Query

from . import queries
from .config import Config
from .types import Instance


class VoltDBCheck(AgentCheck):
    __NAMESPACE__ = 'voltdb'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(VoltDBCheck, self).__init__(*args, **kwargs)
        self._config = Config(cast(Instance, self.instance))

        if self._config.auth is not None:
            password = self._config.auth._password
            self.register_secret(password)

        self._query_manager = QueryManager(
            self,
            self._execute_query_raw,
            queries=[
                # NOTE: This only works on Agent < 7.24.0.
                # On Agent 7.24.0+, wrapping around `Query` is done automatically.
                Query(queries.CPUMetrics),
                Query(queries.MemoryMetrics),
                Query(queries.SnapshotStatusMetrics),
                Query(queries.CommandLogMetrics),
                Query(queries.ProcedureMetrics),
                Query(queries.LatencyMetrics),
                Query(queries.StatementMetrics),
                Query(queries.GCMetrics),
                Query(queries.IOStatsMetrics),
                Query(queries.TableMetrics),
                Query(queries.IndexMetrics),
            ],
            tags=self._config.tags,
        )
        self.check_initializations.append(self._query_manager.compile_queries)

    def _check_can_connect(self):
        # type: () -> None
        url = self._config.api_url
        auth = self._config.auth
        params = self._config.build_api_params(procedure='@SystemInformation')

        try:
            r = self.http.get(url, auth=auth, params=params)
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

    def _execute_query_raw(self, query):
        # type: (str) -> List[tuple]
        component = query

        url = self._config.api_url
        auth = self._config.auth
        params = self._config.build_api_params(procedure='@Statistics', parameters=[component])

        response = self.http.get(url, auth=auth, params=params)
        response.raise_for_status()

        data = response.json()
        return data['results'][0]['data']

    def check(self, _):
        # type: (Any) -> None
        self._check_can_connect()
        self._query_manager.execute()
