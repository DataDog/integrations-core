# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()
DB_NAME = 'data/sample.db'

DB = os.path.join(HERE, DB_NAME)

DEFAULT_INSTANCE = {'db_name': DB}

METRICS_MAP = ['duckdb.worker_threads']
