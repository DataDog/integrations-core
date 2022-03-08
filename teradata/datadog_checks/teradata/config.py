# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.base import is_affirmative

from .common import DEFAULT_COMMAND_TIMEOUT


class TeradataConfig(object):
    def __init__(self, instance):
        # type: (Dict[str, Any]) -> None
        self.dsn = str(instance.get('dsn', ''))
        self.account = str(instance.get('account', ''))
        self.dbc_name = str(instance.get('dbc_name', ''))
        self.db = str(instance.get('database', ''))
        self.driver = str(instance.get('driver', ''))
        self.connection_string = str(instance.get('connection_string', ''))
        self.username = str(instance.get('username', ''))
        self.password = str(instance.get('password', ''))
        self.use_tls = is_affirmative(instance.get('use_tls', False))
        self.https_port = int(instance.get('https_port', 443))
        self.ssl_mode = str(instance.get('ssl_mode', 'Prefer'))
        self.ssl_ca = str(instance.get('ssl_ca', ''))
        self.ssl_ca_path = str(instance.get('ssl_ca_path', ''))
        self.mechanism_key = str(instance.get('mechanism_key', ''))
        self.mechanism_name = str(instance.get('mechanism_name', ''))
        self.tags = instance.get('tags', [])
        self.timeout = int(instance.get('command_timeout', DEFAULT_COMMAND_TIMEOUT))
