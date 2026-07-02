# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
HTTP/JSON client for the VoltDB Management Center (VMC).

Used when the integration is configured with a `url` option. The wire format
matches https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php and is exposed
through the same response shape as the native client (`response.tables[i].
columns[j].name`, `response.tables[i].tuples`) so the check code can be
agnostic to which transport is in use.
"""

import json
from typing import Callable, List, Optional, Union
from urllib.parse import urljoin

import requests

from .client import VoltDBError


class HttpColumn(object):
    __slots__ = ('name',)

    def __init__(self, name: str) -> None:
        self.name = name


class HttpTable(object):
    __slots__ = ('columns', 'tuples')

    def __init__(self, schema: Optional[list], data: Optional[list]) -> None:
        self.columns: List[HttpColumn] = [HttpColumn(entry['name']) for entry in (schema or [])]
        self.tuples: list = data or []


class HttpResponse(object):
    __slots__ = ('status', 'statusString', 'tables')

    SUCCESS = 1

    def __init__(self, json_data: dict) -> None:
        self.status: Optional[int] = json_data.get('status')
        self.statusString: Optional[str] = json_data.get('statusstring')
        self.tables: List[HttpTable] = [
            HttpTable(r.get('schema'), r.get('data')) for r in json_data.get('results') or []
        ]


class HttpClient(object):
    """A wrapper around the VoltDB HTTP/JSON interface (port 8080 by default,
    typically served through the VoltDB Management Center).

    See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
    """

    SUCCESS = HttpResponse.SUCCESS

    def __init__(
        self,
        url: str,
        http_get: Callable[..., requests.Response],
        username: str,
        password: str,
        password_hashed: bool = False,
    ) -> None:
        self._api_url = urljoin(url, '/api/1.0/')
        self._auth = VoltDBAuth(username, password, password_hashed)
        self._http_get = http_get

    def call_procedure(self, procedure: str, params: Union[str, list, None] = None) -> HttpResponse:
        if params is None:
            parameters = ''
        elif isinstance(params, str):
            parameters = params
        else:
            parameters = json.dumps(list(params))

        query = {'Procedure': procedure}
        if parameters:
            query['Parameters'] = parameters

        response = self._http_get(self._api_url, auth=self._auth, params=query)  # SKIP_HTTP_VALIDATION
        response.raise_for_status()
        return HttpResponse(response.json())

    def raise_for_status(self, response: HttpResponse) -> None:
        if response.status != self.SUCCESS:
            raise VoltDBError(response.status, response.statusString)

    def close(self) -> None:
        # Connection pooling is handled by the underlying requests Session.
        return None


class VoltDBAuth(requests.auth.AuthBase):
    def __init__(self, username: str, password: str, password_hashed: bool) -> None:
        self._username = username
        self._password = password
        self._password_hashed = password_hashed

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        # See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
        params = {
            'User': self._username,
            'Hashedpassword' if self._password_hashed else 'Password': self._password,
        }
        r.prepare_url(r.url, params)
        return r
