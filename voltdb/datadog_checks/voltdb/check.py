# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, List, Optional, cast  # noqa: F401

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from .client import Client
from .config import Config
from .types import Instance


class VoltDBCheck(AgentCheck):
    __NAMESPACE__ = 'voltdb'

    def __init__(self, name, init_config, instances):
        # type: (str, dict, list) -> None
        super(VoltDBCheck, self).__init__(name, init_config, instances)

        self._config = Config(
            cast(Instance, self.instance),
            debug=self.log.debug,
            warning=self.log.warning,
        )
        if self._config.password:
            self.register_secret(self._config.password)
        self._client = Client(
            host=self._config.host,
            port=self._config.port,
            username=self._config.username,
            password=self._config.password,
            use_ssl=self._config.use_ssl,
            ssl_config_file=self._config.ssl_config_file,
            connect_timeout=self._config.connect_timeout,
            procedure_timeout=self._config.procedure_timeout,
        )

        self._query_manager = QueryManager(
            self,
            self._execute_query_raw,
            queries=self._config.queries,
            tags=self._config.tags,
        )
        self.check_initializations.append(self._query_manager.compile_queries)

    def _fetch_version(self):
        # type: () -> Optional[str]
        # See: https://docs.voltdb.com/UsingVoltDB/sysprocsysteminfo.php#sysprocsysinforetvalovervw
        response = self._client.call_procedure('@SystemInformation', ['OVERVIEW'])
        self._client.raise_for_status(response)

        rows = response.tables[0].tuples  # type: List[list]

        # NOTE: there will be one VERSION row per server in the cluster.
        # Arbitrarily use the first one we see.
        for row in rows:
            _, column, value = row[0], row[1], row[2]
            if column == 'VERSION':
                return self._transform_version(value)

        self.log.debug('VERSION column not found: %s', [row[1] for row in rows])
        return None

    def _transform_version(self, raw):
        # type: (str) -> Optional[str]
        # VoltDB does not include .0 patch numbers (eg 10.0, not 10.0.0).
        # Need to ensure they're present so the version is always in 3 parts: major.minor.patch.
        try:
            major, rest = raw.split('.', 1)
        except ValueError:
            self.log.debug('Malformed version string: %s', raw)
            return None
        minor, found, patch = rest.partition('.')
        if not found:
            patch = '0'
        return '{}.{}.{}'.format(major, minor, patch)

    @AgentCheck.metadata_entrypoint
    def _submit_version(self, version):
        # type: (str) -> None
        self.set_metadata('version', version)

    def _check_can_connect_and_submit_version(self):
        # type () -> None
        host, port = self._config.netloc
        tags = ['host:{}'.format(host), 'port:{}'.format(port)] + self._config.tags

        try:
            version = self._fetch_version()
        except Exception as exc:
            message = 'Unable to connect to VoltDB: {}'.format(exc)
            self.service_check('can_connect', self.CRITICAL, message=message, tags=tags)
            raise

        self.service_check('can_connect', self.OK, tags=tags)

        if version is not None:
            self._submit_version(version)

    def _execute_query_raw(self, query):
        # type: (str) -> List[tuple]
        # Ad-hoc format: 'A:[B, C]' -> procedure A called with parameters [B, C].
        procedure, params = _parse_query(query)

        response = self._client.call_procedure(procedure, params)
        self._client.raise_for_status(response)

        table = response.tables[0]
        sources = self._config.query_sources.get(query)
        if not sources:
            # Custom query or no source mapping: return rows as-is for QueryManager
            # to consume positionally.
            return [tuple(row) for row in table.tuples]

            # Project the response onto the source columns declared in queries.py,
            # looking them up by name. Missing columns become None so newer/older
            # VoltDB releases that add or drop columns don't break the check.
        col_index = {col.name: i for i, col in enumerate(table.columns)}
        indices = [col_index.get(source) if source else None for source in sources]
        missing = [s for s, i in zip(sources, indices) if s and i is None]
        if missing:
            self.log.debug(
                'VoltDB response for %s is missing columns %s; values will be reported as None.',
                procedure,
                missing,
            )

        return [tuple(row[i] if i is not None else None for i in indices) for row in table.tuples]

    def cancel(self):
        # type: () -> None
        self._client.close()

    def check(self, _):
        # type: (Any) -> None
        self._check_can_connect_and_submit_version()
        self._query_manager.execute()


def _parse_query(query):
    # type: (str) -> tuple
    procedure, _, params_str = query.partition(':')
    procedure = procedure.strip()
    params_str = params_str.strip()
    if not params_str:
        return procedure, []
    if params_str.startswith('[') and params_str.endswith(']'):
        params_str = params_str[1:-1]
    parts = [p.strip() for p in params_str.split(',') if p.strip()]
    params = []
    for part in parts:
        try:
            params.append(int(part))
        except ValueError:
            params.append(part)
    return procedure, params
