# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, Optional  # noqa: F401

import voltdbclient


class VoltDBError(Exception):
    """Raised when a VoltDB procedure call returns a non-success status."""

    def __init__(self, status, status_string):
        # type: (int, Optional[str]) -> None
        super().__init__('VoltDB procedure failed (status={}): {}'.format(status, status_string))
        self.status = status
        self.status_string = status_string


class Client(object):
    """
    A wrapper around the VoltDB native Python client.

    See: https://pypi.org/project/voltdbclient/
    """

    # ClientResponse status code for success.
    # See: voltdbclient.VoltResponse.status
    SUCCESS = 1

    def __init__(
        self,
        host,
        port,
        username='',
        password='',
        use_ssl=False,
        ssl_config_file=None,
        connect_timeout=8,
        procedure_timeout=None,
    ):
        # type: (str, int, str, str, bool, Optional[str], Optional[float], Optional[float]) -> None
        self._host = host
        self._port = port
        self._username = username or ''
        self._password = password or ''
        self._use_ssl = use_ssl
        self._ssl_config_file = ssl_config_file
        self._connect_timeout = connect_timeout
        self._procedure_timeout = procedure_timeout
        self._fser = None  # type: Optional[voltdbclient.FastSerializer]

    def _connect(self):
        # type: () -> voltdbclient.FastSerializer
        return voltdbclient.FastSerializer(
            host=self._host,
            port=self._port,
            usessl=self._use_ssl,
            ssl_config_file=self._ssl_config_file,
            username=self._username,
            password=self._password,
            connect_timeout=self._connect_timeout,
            procedure_timeout=self._procedure_timeout,
            default_cacerts=False,
        )

    def _get_connection(self):
        # type: () -> voltdbclient.FastSerializer
        if self._fser is None:
            self._fser = self._connect()
        return self._fser

    def close(self):
        # type: () -> None
        if self._fser is not None:
            try:
                self._fser.close()
            except Exception:
                pass
            self._fser = None

    def call_procedure(self, procedure, params=None):
        # type: (str, Optional[list]) -> voltdbclient.VoltResponse
        params = list(params) if params else []
        param_types = [_infer_volt_type(p) for p in params]
        try:
            fser = self._get_connection()
            proc = voltdbclient.VoltProcedure(fser, procedure, param_types)
            return proc.call(params)
        except Exception:
            self.close()
            raise

    def raise_for_status(self, response):
        # type: (voltdbclient.VoltResponse) -> None
        if response.status != self.SUCCESS:
            raise VoltDBError(response.status, response.statusString)


def _infer_volt_type(value):
    # type: (object) -> int
    fs = voltdbclient.FastSerializer
    if isinstance(value, bool):
        return fs.VOLTTYPE_TINYINT
    if isinstance(value, int):
        return fs.VOLTTYPE_INTEGER
    if isinstance(value, float):
        return fs.VOLTTYPE_FLOAT
    return fs.VOLTTYPE_STRING
