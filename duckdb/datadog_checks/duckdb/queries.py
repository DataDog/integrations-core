# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


DUCKDB_VERSION = {
    'name': 'version',
    'query': "SELECT version();",
    'columns': [{'name': 'version', 'type': 'source'}],
}

DUCKDDB_WAL = {
    'name': 'wal_autocheckpoint',
    'query': " SELECT CAST(SUBSTR(value, 1, LENGTH(value) - 3) AS BIGINT) * "
    "CASE "
    " WHEN RIGHT(value, 3) = 'KiB' THEN 1024 "
    " WHEN RIGHT(value, 3) = 'MiB' THEN 1024 * 1024 "
    " WHEN RIGHT(value, 3) = 'GiB' THEN 1024 * 1024 * 1024 "
    " WHEN RIGHT(value, 3) = 'TiB' THEN 1024 * 1024 * 1024 * 1024 "
    " ELSE 1 "
    " END AS value_in_bytes FROM duckdb_settings() WHERE name = 'wal_autocheckpoint';",
    'columns': [{'name': 'wal_autocheckpoint', 'type': 'gauge'}],
}


DUCKDDB_THREADS = {
    'name': 'worker_threads',
    'query': "select value from duckdb_settings() where name = 'worker_threads';",
    'columns': [{'name': 'worker_threads', 'type': 'gauge'}],
}


DUCKDB_MEMORY_LIMIT = {
    'name': 'memory_limit',
    'query': " SELECT CAST(SUBSTR(value, 1, LENGTH(value) - 3) AS BIGINT) * "
    "CASE "
    " WHEN RIGHT(value, 3) = 'KiB' THEN 1024 "
    " WHEN RIGHT(value, 3) = 'MiB' THEN 1024 * 1024 "
    " WHEN RIGHT(value, 3) = 'GiB' THEN 1024 * 1024 * 1024 "
    " WHEN RIGHT(value, 3) = 'TiB' THEN 1024 * 1024 * 1024 * 1024 "
    " ELSE 1 "
    " END AS value_in_bytes FROM duckdb_settings() WHERE name = 'memory_limit';",
    'columns': [{'name': 'memory_limit', 'type': 'gauge'}],
}


DUCKDB_PART_WRITE_FLUSH_THRESHOLD = {
    'name': 'partitioned_write_flush_threshold',
    'query': " SELECT  CAST(value AS INTEGER) AS value_as_integer "
    " FROM duckdb_settings() WHERE name = 'partitioned_write_flush_threshold';",
    'columns': [{'name': 'partitioned_write_flush_threshold', 'type': 'gauge'}],
}

DUCKDB_PART_WRITE_MAX_OPEN_FILES = {
    'name': 'partitioned_write_max_open_files',
    'query': " SELECT  CAST(value AS INTEGER) AS value_as_integer "
    " FROM duckdb_settings() WHERE name = 'partitioned_write_max_open_files';",
    'columns': [{'name': 'partitioned_write_max_open_files', 'type': 'gauge'}],
}

DEFAULT_QUERIES = [
    DUCKDB_VERSION,
    DUCKDDB_THREADS,
    DUCKDDB_WAL,
    DUCKDB_MEMORY_LIMIT,
    DUCKDB_PART_WRITE_FLUSH_THRESHOLD,
    DUCKDB_PART_WRITE_MAX_OPEN_FILES,
]
