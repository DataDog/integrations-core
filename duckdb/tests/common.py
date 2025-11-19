# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()
DB_NAME = 'data/sample.db'
WRONG_DB_NAME = 'test.db'

DB = os.path.join(HERE, DB_NAME)

DEFAULT_INSTANCE = {'db_name': DB}
WRONG_INSTANCE = {'db_name': WRONG_DB_NAME}

METRICS_MAP = [
    'duckdb.worker_threads',
    'duckdb.wal_autocheckpoint',
    'duckdb.memory_limit',
    'duckdb.partitioned_write_flush_threshold',
    'duckdb.partitioned_write_max_open_files',
]
