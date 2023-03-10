# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import time

import psycopg2

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.connections import MultiDatabaseConnectionPool


def test_conn_pool(pg_instance):
    check = PostgreSql('postgres', {}, [pg_instance])

    pool = MultiDatabaseConnectionPool(check._new_connection)
    db = pool.get_connection('postgres', 1)
    pool.prune_connections()
    assert len(pool._connections) == 1

    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute("select 1")
        rows = cursor.fetchall()
        assert len(rows) == 1 and rows[0][0] == 1

    time.sleep(1)
    pool.prune_connections()
    assert len(pool._connections) == 0
