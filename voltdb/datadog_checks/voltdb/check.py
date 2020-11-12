# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, List, Optional, cast

import pkg_resources
from six import raise_from

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import Query, QueryManager

from . import queries
from .config import Config
from .types import Instance

BASE_PARSED_VERSION = pkg_resources.get_distribution('datadog-checks-base').parsed_version


class VoltDBCheck(AgentCheck):
    __NAMESPACE__ = 'voltdb'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(VoltDBCheck, self).__init__(*args, **kwargs)
        self._config = Config(cast(Instance, self.instance))

        if self._config.auth is not None:
            password = self._config.auth._password
            self.register_secret(password)

        manager_queries = [
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
        ]

        if BASE_PARSED_VERSION < pkg_resources.parse_version('15.0.0'):
            # On Agent < 7.24.0 we must to pass `Query` objects instead of dicts.
            manager_queries = [Query(query) for query in manager_queries]

        self._query_manager = QueryManager(
            self,
            self._execute_query_raw,
            queries=manager_queries,
            tags=self._config.tags,
        )
        self.check_initializations.append(self._query_manager.compile_queries)

    def _fetch_version(self):
        # type: () -> Optional[str]
        # See: https://docs.voltdb.com/UsingVoltDB/sysprocsysteminfo.php#sysprocsysinforetvalovervw
        url = self._config.api_url
        auth = self._config.auth
        params = self._config.build_api_params(procedure='@SystemInformation', parameters=['OVERVIEW'])

        try:
            r = self.http.get(url, auth=auth, params=params)
        except Exception:
            raise  # For explicitness.

        try:
            r.raise_for_status()
        except Exception as exc:
            message = 'Error response from VoltDB: {}'.format(exc)
            try:
                # Try including detailed error message from response.
                details = r.json()['statusstring']
            except Exception:
                pass
            else:
                message += ' (details: {})'.format(details)
            raise_from(Exception(message), None)

        try:
            data = r.json()
            rows = data['results'][0]['data']  # type: List[tuple]
            # NOTE: there will be one VERSION row per server in the cluster.
            # Arbitrarily use the first one we see.
            return next((value for _, column, value in rows if column == 'VERSION'), None)
        except Exception as exc:
            self.log.debug('Failed to parse version from SystemInformation response:', exc)
            return None

    def _check_can_connect_and_submit_version(self):
        try:
            version = self._fetch_version()
        except Exception as exc:
            message = 'Unable to connect to VoltDB: {}'.format(exc)
            self.service_check('can_connect', self.CRITICAL, message=message, tags=self._config.tags)
            raise

        self.service_check('can_connect', self.OK, tags=self._config.tags)

        if version is not None:
            self.set_metadata('version', version)

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
        self._check_can_connect_and_submit_version()
        self._query_manager.execute()
