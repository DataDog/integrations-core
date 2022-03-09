# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.base import is_affirmative

from .common import DEFAULT_COMMAND_TIMEOUT, DEFAULT_CONNECT_FAILURE_TTL


class TeradataConfig(object):
    def __init__(self, instance):
        # type: (Dict[str, Any]) -> None
        self.use_odbc = is_affirmative(instance.get('use_odbc', True))
        self.use_jdbc = is_affirmative(instance.get('use_jdbc', False))
        self.dsn = str(instance.get('dsn', ''))
        self.account = str(instance.get('account', ''))
        self.host = str(instance.get('host', ''))
        self.port = int(instance.get('port', 1025))
        self.db = str(instance.get('database', ''))
        self.odbc_driver_path = str(instance.get('odbc_driver_path', ''))
        self.jdbc_driver_path = str(instance.get('jdbc_driver_path', ''))
        self.connection_string = str(instance.get('connection_string', ''))
        self.username = str(instance.get('username', ''))
        self.password = str(instance.get('password', ''))
        self.use_tls = is_affirmative(instance.get('use_tls', False))
        self.https_port = int(instance.get('https_port', 443))
        self.ssl_mode = str(instance.get('ssl_mode', 'PREFER'))
        self.ssl_protocol = str(instance.get('ssl_protocol', 'TLSv1.2'))
        self.ssl_ca = str(instance.get('ssl_ca', ''))
        self.ssl_ca_path = str(instance.get('ssl_ca_path', ''))
        self.mechanism_key = str(instance.get('mechanism_key', ''))
        self.mechanism_name = str(instance.get('mechanism_name', ''))
        self.tags = instance.get('tags', [])
        self.timeout = int(instance.get('command_timeout', DEFAULT_COMMAND_TIMEOUT))
        self.connect_failure_ttl = int(instance.get('connect_failure_ttl', DEFAULT_CONNECT_FAILURE_TTL))

    def get(self, option):
        return option
