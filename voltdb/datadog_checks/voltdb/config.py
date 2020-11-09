# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import List, Optional

import requests
from six.moves.urllib.parse import urljoin

from datadog_checks.base import ConfigurationError, is_affirmative

from .types import Instance


class Config(object):
    def __init__(self, instance):
        # type: (Instance) -> None
        url = instance.get('url')  # type: Optional[str]
        username = instance.get('username')  # type: Optional[str]
        password = instance.get('password')  # type: Optional[str]
        password_hashed = is_affirmative(instance.get('password_hashed', False))  # type: bool
        tags = instance.get('tags', [])  # type: List[str]

        if not url:
            raise ConfigurationError('url is required')

        if username and not password:
            raise ConfigurationError('password is required')

        if password and not username:
            raise ConfigurationError('username is required')

        auth = VoltDBAuth(username, password, password_hashed) if username and password else None

        self._url = url
        self._auth = auth
        self.tags = tags

    @property
    def api_url(self):
        # type: () -> str
        return urljoin(self._url, '/api/1.0/')

    @property
    def auth(self):
        # type: () -> Optional[VoltDBAuth]
        return self._auth

    def build_api_params(self, procedure, parameters=None):
        # type: (str, List[str]) -> dict
        # See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php
        params = {'Procedure': procedure}
        if parameters is not None:
            params['Parameters'] = json.dumps(parameters)
        return params


class VoltDBAuth(requests.auth.AuthBase):
    def __init__(self, username, password, password_hashed):
        # type: (str, str, bool) -> None
        self._username = username
        self._password = password
        self._password_hashed = password_hashed

    def __call__(self, r):
        # type: (requests.PreparedRequest) -> requests.PreparedRequest
        # See: https://docs.voltdb.com/UsingVoltDB/ProgLangJson.php#JsonIntro
        params = {'User': self._username, 'Hashedpassword' if self._password_hashed else 'Password': self._password}
        r.prepare_url(r.url, params)
        return r
