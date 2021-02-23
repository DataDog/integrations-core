# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint

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
        self.tags = self._build_tags(instance.get('tags', []))
        self.options = instance.get('options', {}) or {}  # options could be None if empty in the YAML
        replication_channel = self.options.get('replication_channel')
        if replication_channel:
            self.tags.append("channel:{0}".format(replication_channel))
        self.queries = instance.get('queries', [])
        self.ssl = instance.get('ssl', {})
        self.connect_timeout = instance.get('connect_timeout', 10)
        self.max_custom_queries = instance.get('max_custom_queries', DEFAULT_MAX_CUSTOM_QUERIES)
        self.charset = instance.get('charset')
        self.deep_database_monitoring = is_affirmative(instance.get('deep_database_monitoring', False))
        self.statement_metric_limits = instance.get('statement_metric_limits', None)
        self.configuration_checks()

    def _build_tags(self, custom_tags):
        tags = list(set(custom_tags)) or []

        rds_tags = rds_parse_tags_from_endpoint(self.host)
        if rds_tags:
            tags.extend(rds_tags)
        return tags

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
