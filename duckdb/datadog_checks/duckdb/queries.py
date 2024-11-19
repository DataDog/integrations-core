# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

TABLE_STATS = {
    'name': 'tables_number',
    'query': "SELECT table_catalog, COUNT(*) AS num_tables FROM information_schema.tables GROUP BY table_catalog WHERE table_catalog='{}';",
    'columns': [
        {'name': 'table_catalog', 'type': 'tag'},
        {'name': 'num_tables', 'type': 'gauge'},
    ],
}

DUCKDB_VERSION = {
    'name': 'duckdb_version',
    'query': "SELECT version();",
    'columns': [{'name': 'version', 'type': 'source'}],
}


DEFAULT_QUERIES = [TABLE_STATS, DUCKDB_VERSION]
