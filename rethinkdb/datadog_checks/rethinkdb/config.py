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
            raise ConfigurationError('host {!r} must be a string (got {!r})'.format(host, type(host)))

        try:
            port = int(port)
        except (ValueError, TypeError):
            raise ConfigurationError('port {!r} must be convertible to an integer (got {!r})'.format(port, type(port)))

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        if not isinstance(tags, list):
            raise ConfigurationError('tags {!r} must be a list (got {!r})'.format(tags, type(tags)))

        try:
            min_collection_interval = float(min_collection_interval)
        except (ValueError, TypeError):
            raise ConfigurationError(
                'min_collection_interval {!r} must be convertible to a number (got {!r})'.format(
                    min_collection_interval, type(min_collection_interval)
                )
            )

        self.host = host  # type: str
        self.port = port  # type: int
        self.user = user  # type: Optional[str]
        self.password = password  # type: Optional[str]
        self.tls_ca_cert = tls_ca_cert  # type: Optional[str]
        self.tags = tags  # type: List[str]
        self.min_collection_interval = min_collection_interval  # type: float

    @property
    def service_check_tags(self):
        # type: () -> List[str]
        return ['host:{}'.format(self.host), 'port:{}'.format(self.port)] + self.tags
