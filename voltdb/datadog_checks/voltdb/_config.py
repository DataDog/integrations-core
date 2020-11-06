# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import List, Optional, Tuple

from datadog_checks.base import ConfigurationError, is_affirmative

from ._types import Instance


class Config(object):
    def __init__(self, instance):
        # type: (Instance) -> None
        host = instance.get('host')  # type: Optional[str]
        port = instance.get('port')  # type: Optional[int]
        username = instance.get('username')  # type: Optional[str]
        password = instance.get('password')  # type: Optional[str]
        password_hashed = is_affirmative(instance.get('password_hashed', False))  # type: bool
        tags = instance.get('tags', [])  # type: List[str]

        if not host:
            raise ConfigurationError('host is required')

        if username and not password:
            raise ConfigurationError('password is required')

        if password and not username:
            raise ConfigurationError('username is required')

        auth = (username, password) if username and password else None

        self._host = host
        self._port = port
        self._auth = auth
        self._password_hashed = password_hashed
        self.tags = tags

    @property
    def auth(self):
        # type: () -> Optional[Tuple[str, str]]
        return self._auth

    @property
    def api_url(self):
        # type: () -> str
        netloc = self._host
        if self._port is not None:
            netloc += ':{}'.format(self._port)
        return 'http://{}/api/1.0/'.format(netloc)

    def build_api_params(self, procedure, parameters=None):
        # type: (str, List[str]) -> dict
        # See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php
        params = {'Procedure': procedure}

        if parameters is not None:
            params['Parameters'] = json.dumps(parameters)

        if self._auth is not None:
            username, password = self._auth
            params['User'] = username
            params['Hashedpassword' if self._password_hashed else 'Password'] = password

        return params
