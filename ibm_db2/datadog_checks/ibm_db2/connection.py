# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterator

import ibm_db
from requests import ConnectionError

from .utils import scrub_connection_string

if TYPE_CHECKING:
    from .config_models import InstanceConfig
    from .ibm_db2 import IbmDb2Check


def get_connection_data(
    db: str,
    username: str,
    password: str,
    host: str | None,
    port: int | None,
    security: str | None,
    tls_cert: str | None,
    connection_timeout: int | None,
) -> tuple[str, str, str]:
    if host:
        target = 'database={};hostname={};port={};protocol=tcpip;uid={};pwd={}'.format(
            db, host, port, username, password
        )
        username = ''
        password = ''
        if security == 'ssl':
            target = '{};security=ssl;'.format(target)
        if tls_cert:
            target = '{};security=ssl;sslservercertificate={}'.format(target, tls_cert)
        if connection_timeout:
            target = '{};connecttimeout={}'.format(target, connection_timeout)
    else:  # no cov
        target = db

    return target, username, password


class Db2Connection:
    def __init__(self, check: IbmDb2Check, config: InstanceConfig):
        self._check = check
        self._config = config
        self.conn = None

    def connect(self) -> None:
        """Open a new connection, leaving `conn` as `None` if it fails."""
        target, username, password = get_connection_data(
            self._config.db,
            self._config.username,
            self._config.password,
            self._config.host,
            self._config.port,
            self._config.security,
            self._config.tls_cert,
            self._config.connection_timeout,
        )

        # Get column names in lower case
        connection_options = {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER}

        try:
            self._check.log.debug("Attempting to connect to Db2 with `%s`...", scrub_connection_string(target))
            self.conn = ibm_db.connect(target, username, password, connection_options)
        except Exception as e:
            if self._config.host:
                self._check.log.error('Unable to connect with `%s`: %s', scrub_connection_string(target), e)
            else:  # no cov
                self._check.log.error('Unable to connect to database `%s` as user `%s`: %s', target, username, e)
            self.conn = None

    def iter_rows(self, query: str, method: Callable[[Any], Any]) -> Iterator[Any]:
        """
        Execute `query` and yield rows fetched with `method` (an `ibm_db` fetch function).

        If execution fails, reconnects once and retries, emitting the connection service check. Raises
        `requests.ConnectionError` if the reconnect fails.
        """
        # https://github.com/ibmdb/python-ibmdb/wiki/APIs
        try:
            cursor = ibm_db.exec_immediate(self.conn, query)
        except Exception as e:
            error = str(e)
            self._check.log.error("Error executing query: %s.\nAttempting to reconnect", error)
            # ToDo: Probably the best strategy here would be to just set self.conn = None, abort the current check run
            # and retry on the next check run.
            self.connect()
            self._check.emit_connection_service_checks()
            if self.conn is None:
                raise ConnectionError("Unable to create new connection")

            cursor = ibm_db.exec_immediate(self.conn, query)

        row = method(cursor)
        while row is not False:
            yield row

            # Get next row, if any
            row = method(cursor)
