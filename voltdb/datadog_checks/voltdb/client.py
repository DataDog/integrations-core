# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
from concurrent.futures import Future
from typing import List, Optional, Tuple

import voltdbclient
from voltclient import VoltClient, VoltConnectionError, VoltNoConnectionsError


class VoltDBError(Exception):
    """Raised when a VoltDB procedure call returns a non-success status."""

    def __init__(self, status: int, status_string: Optional[str]) -> None:
        super().__init__('VoltDB procedure failed (status={}): {}'.format(status, status_string))
        self.status = status
        self.status_string = status_string


class Client(object):
    """
    Wrapper around the topology-aware `voltclient.VoltClient`.

    The configured endpoints are seeds: the client discovers the full cluster
    membership at connect time, keeps a connection to every node, and routes
    each call to the node that executes it. Node failures, rejoins, and elastic
    expansions are picked up in the background without reconnecting.

    See: https://pypi.org/project/voltdbclient/
    """

    # ClientResponse status code for success.
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
        self._connect_timeout = connect_timeout or 8
        # VoltClient enforces a deadline on every call, so "no timeout" becomes the
        # largest wait the threading primitives accept.
        self._procedure_timeout = procedure_timeout if procedure_timeout is not None else threading.TIMEOUT_MAX
        self._log = log
        self._client: Optional[VoltClient] = None

        # VoltClient takes a single port shared by all seeds.
        self._hosts = [host for host, _ in self._endpoints]
        self._port = self._endpoints[0][1]
        ports = sorted({port for _, port in self._endpoints})
        if len(ports) > 1:
            self._log_warning(
                'VoltDB endpoints declare different ports %s; the client connects to every seed on port %d.',
                ports,
                self._port,
            )

    def _log_debug(self, *args) -> None:
        if self._log is not None:
            self._log.debug(*args)

    def _log_warning(self, *args) -> None:
        if self._log is not None:
            self._log.warning(*args)

    def _get_client(self) -> VoltClient:
        if self._client is None:
            self._client = VoltClient(
                hosts=self._hosts,
                port=self._port,
                username=self._username,
                password=self._password,
                usessl=self._use_ssl,
                ssl_config_file=self._ssl_config_file,
                connect_timeout=self._connect_timeout,
                procedure_timeout=self._procedure_timeout,
                default_cacerts=False,
            )
            self._log_debug('VoltDB client connected via seeds %s on port %d', self._hosts, self._port)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    @property
    def endpoints(self) -> List[Tuple[str, int]]:
        return list(self._endpoints)

    def call_procedure_async(self, procedure: str, params: Optional[list] = None) -> Future:
        """Send a procedure call without waiting; returns a Future for its VoltResponse."""
        params = list(params) if params else []
        param_types = [_infer_volt_type(p) for p in params]
        had_client = self._client is not None
        try:
            return self._get_client().call_async(procedure, param_types, params)
        except VoltNoConnectionsError:
            # Every pooled connection is gone. Rebuild from the configured seeds, whose
            # addresses may have changed (e.g. a full cluster restart), and send once more.
            self.close()
            if not had_client:
                raise
            self._log_debug('VoltDB pool has no live connections; reconnecting from the seeds.')
            return self._get_client().call_async(procedure, param_types, params)

    def result(self, future: Future, procedure: str, params: Optional[list] = None) -> voltdbclient.VoltResponse:
        """Wait for a call sent with call_procedure_async. If its connection was lost while it
        was in flight, send it once more: monitoring calls only read data, so a resend is safe."""
        try:
            return future.result()
        except VoltConnectionError as exc:
            self._log_debug('VoltDB call to %s lost its connection (%s); sending it once more.', procedure, exc)
            return self.call_procedure_async(procedure, params).result()

    def call_procedure(self, procedure: str, params: Optional[list] = None) -> voltdbclient.VoltResponse:
        return self.result(self.call_procedure_async(procedure, params), procedure, params)

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
