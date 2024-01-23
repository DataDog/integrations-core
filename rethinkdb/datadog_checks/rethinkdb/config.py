# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, Optional  # noqa: F401

from datadog_checks.base import ConfigurationError

from .types import Instance  # noqa: F401


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

        if not isinstance(host, str):
            raise ConfigurationError('host {!r} must be a string (got {!r})'.format(host, type(host)))

        try:
            port = int(port)
        except (ValueError, TypeError):
            raise ConfigurationError('port {!r} must be convertible to an integer (got {!r})'.format(port, type(port)))

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        if not isinstance(tags, list):
            raise ConfigurationError('tags {!r} must be a list (got {!r})'.format(tags, type(tags)))

        self.host = host  # type: str
        self.port = port  # type: int
        self.user = user  # type: Optional[str]
        self.password = password  # type: Optional[str]
        self.tls_ca_cert = tls_ca_cert  # type: Optional[str]
        self.tags = tags  # type: List[str]
        self.service_check_tags = ('host:{}'.format(self.host), 'port:{}'.format(self.port)) + tuple(self.tags)
