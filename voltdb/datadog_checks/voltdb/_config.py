# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Optional, List, Tuple
from datadog_checks.base import ConfigurationError

from ._types import Instance


class Config(object):
    def __init__(self, instance):
        # type: (Instance) -> None
        hostname = instance.get('hostname')  # type: Optional[str]
        port = instance.get('port')  # type: Optional[int]
        username = instance.get('username')  # type: Optional[str]
        password = instance.get('password')  # type: Optional[str]
        tags = instance.get('tags', [])  # type: List[str]

        if not hostname:
            raise ConfigurationError('hostname is required')

        if username and not password:
            raise ConfigurationError('password is required')

        if password and not username:
            raise ConfigurationError('username is required')

        auth = (username, password) if username and password else None

        self._hostname = hostname
        self._port = port
        self._auth = auth
        self.tags = tags

    @property
    def auth(self):
        # type: () -> Optional[Tuple[str, str]]
        return self._auth

    @property
    def api_url(self):
        # type: () -> str
        netloc = self._hostname
        if self._port is not None:
            netloc += ':{}'.format(self._port)
        return 'http://{}/api/1.0/'.format(netloc)

    def build_api_params(self, procedure, parameters):
        # type: (str, List[str]) -> dict
        # See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php
        params = {
            'Procedure': procedure,
            'Parameters': json.dumps(parameters),
            'admin': 'false',
        }

        if self._auth is not None:
            user, password = self._auth
            params['User'] = user
            params['Password'] = password

        return params
