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

    def __init__(self, instance=None):
        # type: (Instance) -> None
        if instance is None:
            instance = {}

        host = instance.get('host', 'localhost')
        port = instance.get('port', 28015)
        user = instance.get('username')
        password = instance.get('password')
        tls_ca_cert = instance.get('tls_ca_cert')
        tags = instance.get('tags', [])
        min_collection_interval = instance.get('min_collection_interval', 15)

        if not isinstance(host, str):
            raise ConfigurationError('host must be a string (got {!r})'.format(type(host)))

        if not isinstance(port, int) or isinstance(port, bool):
            raise ConfigurationError('port must be an integer (got {!r})'.format(type(port)))

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        try:
            min_collection_interval = float(min_collection_interval)
        except (ValueError, TypeError):
            raise ConfigurationError(
                'min_collection_interval must be convertible to a number (got {!r})'.format(
                    type(min_collection_interval)
                )
            )

        self.host = host  # type: str
        self.port = port  # type: int
        self.user = user  # type: Optional[str]
        self.password = password  # type: Optional[str]
        self.tls_ca_cert = tls_ca_cert  # type: Optional[str]
        self.tags = tags  # type: List[str]
        self.min_collection_interval = min_collection_interval  # type: float
