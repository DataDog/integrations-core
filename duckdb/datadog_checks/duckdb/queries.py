# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# TABLE_STATS = {
#     'name': 'tables_number',
#     'query': "SELECT table_catalog, COUNT(*) AS num_tables FROM information_schema.tables "
#     "GROUP BY table_catalog WHERE table_catalog='{}';",
#     'columns': [
#         {'name': 'table_catalog', 'type': 'tag'},
#         {'name': 'num_tables', 'type': 'gauge'},
#     ],
# }

DUCKDB_VERSION = {
    'name': 'duckdb_version',
    'query': "SELECT version();",
    'columns': [{'name': 'version', 'type': 'source'}],
}

DUCKDDB_WAL = {
    'name': 'duckdb_wal',
    'query': " SELECT CAST(SUBSTR(value, 1, LENGTH(value) - 3) AS INTEGER) * "
    "CASE "
    " WHEN RIGHT(value, 3) = 'KiB' THEN 1024 "
    " WHEN RIGHT(value, 3) = 'MiB' THEN 1024 * 1024 "
    " WHEN RIGHT(value, 3) = 'GiB' THEN 1024 * 1024 * 1024 "
    " WHEN RIGHT(value, 3) = 'TiB' THEN 1024 * 1024 * 1024 * 1024 "
    " ELSE 1 "
    " END AS value_in_bytes FROM duckdb_settings() WHERE name = 'wal_autocheckpoint';",
    'columns': [{'name': 'wal_autocheckpoint', 'type': 'gauge'}],
}

DUCKDDB_WAL_2 = {
    'name': 'duckdb_worker_threads',
    'query': " select value from duckdb_settings() where name = 'worker_threads';",
    'columns': [{'name': 'worker_threads', 'type': 'gauge'}],
}

DEFAULT_QUERIES = [DUCKDDB_WAL_2]
