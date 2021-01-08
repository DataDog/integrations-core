# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable, List, Optional

from six.moves.urllib.parse import urlparse

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

        parsed_url = urlparse(url)

        host = parsed_url.hostname
        if not host:  # pragma: no cover  # Mostly just type safety.
            raise ConfigurationError('URL must contain a host')

        port = parsed_url.port
        if not port:
            port = 443 if parsed_url.scheme == 'https' else 80
            self._debug('No port detected, defaulting to port %d', port)

        self.url = url
        self.netloc = (host, port)
        self.username = username
        self.password = password
        self.password_hashed = password_hashed
        self.tags = tags
