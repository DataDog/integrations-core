# (C) Datadog, Inc. 2020-present
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
from typing import Callable, List, Optional, Union  # noqa: F401
from urllib.parse import urljoin

import requests

from .client import VoltDBError


class HttpColumn(object):
    __slots__ = ('name',)

    def __init__(self, name):
        # type: (str) -> None
        self.name = name


class HttpTable(object):
    __slots__ = ('columns', 'tuples')

    def __init__(self, schema, data):
        # type: (Optional[list], list) -> None
        self.columns = [HttpColumn(entry['name']) for entry in (schema or [])]
        self.tuples = data or []


class HttpResponse(object):
    __slots__ = ('status', 'statusString', 'tables')

    SUCCESS = 1

    def __init__(self, json_data):
        # type: (dict) -> None
        self.status = json_data.get('status')
        self.statusString = json_data.get('statusstring')
        self.tables = [HttpTable(r.get('schema'), r.get('data')) for r in json_data.get('results') or []]


class HttpClient(object):
    """A wrapper around the VoltDB HTTP/JSON interface (port 8080 by default,
    typically served through the VoltDB Management Center).

    See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
    """

    SUCCESS = HttpResponse.SUCCESS

    def __init__(self, url, http_get, username, password, password_hashed=False):
        # type: (str, Callable[..., requests.Response], str, str, bool) -> None
        self._api_url = urljoin(url, '/api/1.0/')
        self._auth = VoltDBAuth(username, password, password_hashed)
        self._http_get = http_get

    def call_procedure(self, procedure, params=None):
        # type: (str, Union[str, list, None]) -> HttpResponse
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

    def raise_for_status(self, response):
        # type: (HttpResponse) -> None
        if response.status != self.SUCCESS:
            raise VoltDBError(response.status, response.statusString)

    def close(self):
        # type: () -> None
        # Connection pooling is handled by the underlying requests Session.
        return None


class VoltDBAuth(requests.auth.AuthBase):
    def __init__(self, username, password, password_hashed):
        # type: (str, str, bool) -> None
        self._username = username
        self._password = password
        self._password_hashed = password_hashed

    def __call__(self, r):
        # type: (requests.PreparedRequest) -> requests.PreparedRequest
        # See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
        params = {
            'User': self._username,
            'Hashedpassword' if self._password_hashed else 'Password': self._password,
        }
        r.prepare_url(r.url, params)
        return r
