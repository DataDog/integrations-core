# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import ConfigurationError
from datadog_checks.base.log import get_check_logger

DEFAULT_MAX_CUSTOM_QUERIES = 20


class MySQLConfig(object):
    def __init__(self, instance):
        self.log = get_check_logger()
        self.host = instance.get('host', instance.get('server', ''))
        self.port = int(instance.get('port', 0))
        self.tags = list(instance.get('tags', []))
        self.mysql_sock = instance.get('sock', '')
        self.defaults_file = instance.get('defaults_file', '')
        self.user = instance.get('user', '')
        self.password = str(instance.get('pass', ''))
        self.tags = instance.get('tags', [])
        self.options = instance.get('options', {}) or {}  # options could be None if empty in the YAML
        self.queries = instance.get('queries', [])
        self.ssl = instance.get('ssl', {})
        self.connect_timeout = instance.get('connect_timeout', 10)
        self.max_custom_queries = instance.get('max_custom_queries', DEFAULT_MAX_CUSTOM_QUERIES)
        self.charset = instance.get('charset')
        self.configuration_checks()

    def configuration_checks(self):
        if self.queries or self.max_custom_queries != DEFAULT_MAX_CUSTOM_QUERIES:
            self.log.warning(
                'The options `queries` and `max_custom_queries` are deprecated and will be '
                'removed in a future release. Use the `custom_queries` option instead.'
            )

        if not (self.host and self.user) and not self.defaults_file:
            raise ConfigurationError("Mysql host and user or a defaults_file are needed.")

        if (self.host or self.user or self.port or self.mysql_sock) and self.defaults_file:
            self.log.warning(
                "Both connection details and defaults_file have been specified, connection details will be ignored"
            )

        if self.mysql_sock and self.host:
            self.log.warning("Both socket and host have been specified, socket will be used")
