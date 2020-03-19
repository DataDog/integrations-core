# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, Optional

from datadog_checks.base import ConfigurationError

from .types import Instance


class Config(object):
    """
    Hold instance configuration for a RethinkDB check.

    Encapsulates the validation of an `instance` dictionary while improving type information.
    """

    def __init__(self, instance):
        # type: (Instance) -> None
        host = instance.get('host', 'localhost')
        port = instance.get('port', 28015)
        user = instance.get('username')
        password = instance.get('password')
        tls_ca_cert = instance.get('tls_ca_cert')
        tags = instance.get('tags', [])

        if not isinstance(host, str):
            raise ConfigurationError('host must be a string (got {!r})'.format(type(host)))

        if not isinstance(port, int) or isinstance(port, bool):
            raise ConfigurationError('port must be an integer (got {!r})'.format(type(port)))

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        self.host = host  # type: str
        self.port = port  # type: int
        self.user = user  # type: Optional[str]
        self.password = password  # type: Optional[str]
        self.tls_ca_cert = tls_ca_cert  # type: Optional[str]
        self.tags = tags  # type: List[str]

    def __repr__(self):
        # type: () -> str
        return (
            'Config(host={host!r}, '
            'port={port!r}, '
            'user={user!r}, '
            "password={password!r}, "
            'tls_ca_cert={tls_ca_cert!r}, '
            'tags={tags!r})'
        ).format(
            host=self.host,
            port=self.port,
            user=self.user,
            password='********' if self.password else '',
            tls_ca_cert=self.tls_ca_cert,
            tags=self.tags,
        )
