# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Callable, List, Optional, Tuple, Union

import requests
from six.moves.urllib.parse import urljoin, urlparse

from datadog_checks.base import ConfigurationError, is_affirmative

from .types import Instance


class Config(object):
    def __init__(self, instance, debug=lambda *args: None):
        # type: (Instance, Callable) -> None
        self._debug = debug

        url = instance.get('url')  # type: Optional[str]
        username = instance.get('username')  # type: Optional[str]
        password = instance.get('password')  # type: Optional[str]
        password_hashed = is_affirmative(instance.get('password_hashed', False))  # type: bool
        tags = instance.get('tags', [])  # type: List[str]

        if not url:
            raise ConfigurationError('url is required')

        if not username or not password:
            raise ConfigurationError('username and password are required')

        auth = VoltDBAuth(username, password, password_hashed)

        parsed_url = urlparse(url)

        host = parsed_url.hostname
        if not host:  # pragma: no cover  # Mostly just type safety.
            raise ConfigurationError('URL must contain a host')

        port = parsed_url.port
        if not port:
            port = 443 if parsed_url.scheme == 'https' else 80
            self._debug('No port detected, defaulting to port %d', port)

        self._url = url
        self._host = host
        self._port = port
        self._auth = auth
        self.tags = tags

    @property
    def api_url(self):
        # type: () -> str
        # See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php
        return urljoin(self._url, '/api/1.0/')

    @property
    def netloc(self):
        # type: () -> Tuple[str, int]
        return self._host, self._port

    @property
    def auth(self):
        # type: () -> Optional[VoltDBAuth]
        return self._auth

    def build_api_params(self, procedure, parameters=None):
        # type: (str, Union[str, List[str]]) -> dict
        # See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php
        params = {'Procedure': procedure}

        if parameters:
            if not isinstance(parameters, str):
                parameters = json.dumps(parameters)
            params['Parameters'] = parameters

        return params


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
