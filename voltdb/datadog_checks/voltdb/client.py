# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Callable, Union  # noqa: F401

import requests
from six.moves.urllib.parse import urljoin


class Client(object):
    """
    A wrapper around the VoltDB HTTP JSON interface.

    See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
    """

    def __init__(self, url, http_get, username, password, password_hashed=False):
        # type: (str, Callable[..., requests.Response], str, str, bool) -> None
        self._api_url = urljoin(url, '/api/1.0/')
        self._auth = VoltDBAuth(username, password, password_hashed)
        self._http_get = http_get

    def request(self, procedure, parameters=None):
        # type: (str, Union[str, list]) -> requests.Response
        url = self._api_url
        auth = self._auth
        params = {'Procedure': procedure}

        if parameters:
            if not isinstance(parameters, str):
                parameters = json.dumps(parameters)
            params['Parameters'] = parameters

        return self._http_get(url, auth=auth, params=params)  # SKIP_HTTP_VALIDATION


class VoltDBAuth(requests.auth.AuthBase):
    def __init__(self, username, password, password_hashed):
        # type: (str, str, bool) -> None
        self._username = username
        self._password = password
        self._password_hashed = password_hashed

    def __call__(self, r):
        # type: (requests.PreparedRequest) -> requests.PreparedRequest
        # See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
        params = {'User': self._username, 'Hashedpassword' if self._password_hashed else 'Password': self._password}
        r.prepare_url(r.url, params)
        return r
