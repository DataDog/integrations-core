# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, List, Optional, cast  # noqa: F401

import requests  # noqa: F401
from six import raise_from

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

        self._config = Config(cast(Instance, self.instance), debug=self.log.debug)
        self.register_secret(self._config.password)
        self._client = Client(
            url=self._config.url,
            http_get=self.http.get,
            username=self._config.username,
            password=self._config.password,
            password_hashed=self._config.password_hashed,
        )

        self._query_manager = QueryManager(
            self,
            self._execute_query_raw,
            queries=self._config.queries,
            tags=self._config.tags,
        )
        self.check_initializations.append(self._query_manager.compile_queries)

    def _raise_for_status_with_details(self, response):
        # type: (requests.Response) -> None
        try:
            response.raise_for_status()
        except Exception as exc:
            message = 'Error response from VoltDB: {}'.format(exc)
            try:
                # Try including detailed error message from response.
                details = response.json()['statusstring']
            except Exception:
                pass
            else:
                message += ' (details: {})'.format(details)
            raise_from(Exception(message), exc)

    def _fetch_version(self):
        # type: () -> Optional[str]
        # See: https://docs.voltdb.com/UsingVoltDB/sysprocsysteminfo.php#sysprocsysinforetvalovervw
        response = self._client.request('@SystemInformation', parameters=['OVERVIEW'])
        self._raise_for_status_with_details(response)

        data = response.json()
        rows = data['results'][0]['data']  # type: List[tuple]

        # NOTE: there will be one VERSION row per server in the cluster.
        # Arbitrarily use the first one we see.
        for _, column, value in rows:
            if column == 'VERSION':
                return self._transform_version(value)

        self.log.debug('VERSION column not found: %s', [column for _, column, _ in rows])
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
        # Ad-hoc format, close to the HTTP API format.
        # Eg 'A:[B, C]' -> '?Procedure=A&Parameters=[B, C]'
        procedure, _, parameters = query.partition(":")

        response = self._client.request(procedure, parameters=parameters)
        self._raise_for_status_with_details(response)

        data = response.json()
        return data['results'][0]['data']

    def check(self, _):
        # type: (Any) -> None
        self._check_can_connect_and_submit_version()
        self._query_manager.execute()
