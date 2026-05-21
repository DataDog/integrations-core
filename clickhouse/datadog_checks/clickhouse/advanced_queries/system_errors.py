# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# https://clickhouse.com/docs/operations/system-tables/errors
SystemErrors = {
    'name': 'system.errors',
    'query': 'SELECT value, name, code, remote FROM system.errors WHERE value > 0',
    'columns': [
        {'name': 'errors.raised', 'type': 'monotonic_count'},
        {'name': 'error_name', 'type': 'tag'},
        {'name': 'error_code', 'type': 'tag'},
        {'name': 'remote', 'type': 'tag', 'boolean': True},
    ],
}
