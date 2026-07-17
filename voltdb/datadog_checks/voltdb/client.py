# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Callable, Union  # noqa: F401
from urllib.parse import urljoin

from datadog_checks.base.utils.http_protocol import HTTPResponse  # noqa: F401


class Client(object):
    """
    A wrapper around the VoltDB HTTP JSON interface.

    See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
    """

    def __init__(self, url, http_get, username, password, password_hashed=False):
        # type: (str, Callable[..., HTTPResponse], str, str, bool) -> None
        self._api_url = urljoin(url, '/api/1.0/')
        self._username = username
        self._password = password
        self._password_field = 'Hashedpassword' if password_hashed else 'Password'
        self._http_get = http_get

    def request(self, procedure, parameters=None):
        # type: (str, Union[str, list]) -> HTTPResponse
        url = self._api_url
        params = {'Procedure': procedure}

        if parameters:
            if not isinstance(parameters, str):
                parameters = json.dumps(parameters)
            params['Parameters'] = parameters

        # VoltDB expects credentials as query params.
        # See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
        params['User'] = self._username
        params[self._password_field] = self._password

        return self._http_get(url, params=params)  # SKIP_HTTP_VALIDATION
