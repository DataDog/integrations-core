# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

log = logging.getLogger(__name__)

DEFAULT_MAX_CUSTOM_QUERIES = 20


def get_config(instance):
    host = instance.get('server', '')
    port = int(instance.get('port', 0))
    mysql_sock = instance.get('sock', '')
    defaults_file = instance.get('defaults_file', '')
    user = instance.get('user', '')
    password = str(instance.get('pass', ''))
    tags = instance.get('tags', [])
    options = instance.get('options', {}) or {}  # options could be None if empty in the YAML
    queries = instance.get('queries', [])
    ssl = instance.get('ssl', {})
    connect_timeout = instance.get('connect_timeout', 10)
    max_custom_queries = instance.get('max_custom_queries', DEFAULT_MAX_CUSTOM_QUERIES)

    if queries or 'max_custom_queries' in instance:
        log.warning(
            'The options `queries` and `max_custom_queries` are deprecated and will be '
            'removed in a future release. Use the `custom_queries` option instead.'
        )

    return (
        host,
        port,
        user,
        password,
        mysql_sock,
        defaults_file,
        tags,
        options,
        queries,
        ssl,
        connect_timeout,
        max_custom_queries,
    )
