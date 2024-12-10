# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 5000
DB = 'data/duckdb.db'

DEFAULT_INSTANCE = {'host': HOST, 'port': PORT, 'database': DB, 'read_only': False}

