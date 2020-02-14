# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Dict

from datadog_checks.base import ConfigurationError


class Config:
    def __init__(self, instance):
        # type: (Dict[str, Any]) -> None
        host = instance.get('host', 'localhost')
        port = instance.get('port', 28015)

        if not isinstance(host, str):
            raise ConfigurationError('host must be a string (got {!r})'.format(type(host)))

        if isinstance(port, bool) or not isinstance(port, int):
            raise ConfigurationError('port must be an integer (got {!r})'.format(type(port)))

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        self.host = host  # type: str
        self.port = port  # type: int

    def __repr__(self):
        # type: () -> str
        return 'Config(host={host!r}, port={port!r})'.format(host=self.host, port=self.port)
