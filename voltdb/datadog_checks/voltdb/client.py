# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, Optional, Tuple

import voltdbclient


class VoltDBError(Exception):
    """Raised when a VoltDB procedure call returns a non-success status."""

    def __init__(self, status: int, status_string: Optional[str]) -> None:
        super().__init__('VoltDB procedure failed (status={}): {}'.format(status, status_string))
        self.status = status
        self.status_string = status_string


class Client(object):
    """
    A wrapper around the VoltDB native Python client.

    Accepts one or more `(host, port)` endpoints. On a connect failure the
    client transparently tries the next endpoint, so the Agent can keep
    collecting metrics as long as at least one cluster member is reachable.

    See: https://pypi.org/project/voltdbclient/
    """

    # ClientResponse status code for success.
    # See: voltdbclient.VoltResponse.status
    SUCCESS = 1

    def __init__(
        self,
        endpoints: List[Tuple[str, int]],
        username: str = '',
        password: str = '',
        use_ssl: bool = False,
        ssl_config_file: Optional[str] = None,
        connect_timeout: Optional[float] = 8,
        procedure_timeout: Optional[float] = None,
        log: Optional[object] = None,
    ) -> None:
        if not endpoints:
            raise ValueError('Client requires at least one (host, port) endpoint')
        self._endpoints = list(endpoints)
        self._username = username or ''
        self._password = password or ''
        self._use_ssl = use_ssl
        self._ssl_config_file = ssl_config_file
        self._connect_timeout = connect_timeout
        self._procedure_timeout = procedure_timeout
        self._fser: Optional[voltdbclient.FastSerializer] = None
        self._active: Optional[Tuple[str, int]] = None
        self._log = log

    def _log_debug(self, *args) -> None:
        if self._log is not None:
            self._log.debug(*args)

    def _log_warning(self, *args) -> None:
        if self._log is not None:
            self._log.warning(*args)

    def _open(self, host: str, port: int) -> voltdbclient.FastSerializer:
        return voltdbclient.FastSerializer(
            host=host,
            port=port,
            usessl=self._use_ssl,
            ssl_config_file=self._ssl_config_file,
            username=self._username,
            password=self._password,
            connect_timeout=self._connect_timeout,
            procedure_timeout=self._procedure_timeout,
            default_cacerts=False,
        )

    def _connect_any(self) -> voltdbclient.FastSerializer:
        """Try each configured endpoint until one connects. Raises the last
        exception if every endpoint fails."""
        last_exc: Optional[BaseException] = None
        for host, port in self._endpoints:
            try:
                fser = self._open(host, port)
            except Exception as exc:  # noqa: BLE001
                self._log_warning('VoltDB endpoint %s:%d unreachable (%s); trying the next one.', host, port, exc)
                last_exc = exc
                continue
            self._active = (host, port)
            self._log_debug('VoltDB connected to %s:%d', host, port)
            return fser
        # Exhausted all endpoints.
        assert last_exc is not None
        raise last_exc

    def _get_connection(self) -> voltdbclient.FastSerializer:
        if self._fser is None:
            self._fser = self._connect_any()
        return self._fser

    def close(self) -> None:
        if self._fser is not None:
            try:
                self._fser.close()
            except Exception:
                pass
            self._fser = None
            self._active = None

    @property
    def endpoints(self) -> List[Tuple[str, int]]:
        return list(self._endpoints)

    @property
    def active_endpoint(self) -> Optional[Tuple[str, int]]:
        return self._active

    def call_procedure(self, procedure: str, params: Optional[list] = None) -> voltdbclient.VoltResponse:
        params = list(params) if params else []
        param_types = [_infer_volt_type(p) for p in params]
        # If we already have a connection, try it first. If it errors, close
        # and retry once against the full endpoint list. This handles the
        # common case where the active node went down between check runs.
        had_connection = self._fser is not None
        try:
            fser = self._get_connection()
            proc = voltdbclient.VoltProcedure(fser, procedure, param_types)
            return proc.call(params)
        except Exception:
            self.close()
            if not had_connection:
                # First attempt already iterated every endpoint via _connect_any.
                raise

        # Second attempt: reconnect to any endpoint and retry the call once.
        self._log_debug('VoltDB call to %s failed; reconnecting and retrying once.', procedure)
        fser = self._get_connection()
        try:
            proc = voltdbclient.VoltProcedure(fser, procedure, param_types)
            return proc.call(params)
        except Exception:
            self.close()
            raise

    def raise_for_status(self, response: voltdbclient.VoltResponse) -> None:
        if response.status != self.SUCCESS:
            raise VoltDBError(response.status, response.statusString)


def _infer_volt_type(value: object) -> int:
    fs = voltdbclient.FastSerializer
    if isinstance(value, bool):
        return fs.VOLTTYPE_TINYINT
    if isinstance(value, int):
        return fs.VOLTTYPE_INTEGER
    if isinstance(value, float):
        return fs.VOLTTYPE_FLOAT
    return fs.VOLTTYPE_STRING
