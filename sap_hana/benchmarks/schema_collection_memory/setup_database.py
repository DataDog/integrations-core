# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
#!/usr/bin/env python3
"""Create the datadog monitoring user and populate the BENCH schema with NUM_TABLES x NUM_COLUMNS tables."""

from __future__ import annotations

import argparse
import sys
from contextlib import closing

NUM_TABLES = 1000
NUM_COLUMNS = 1000

ADMIN_USER = "system"
ADMIN_PASSWORD = "Admin1337"
DATADOG_USER = "datadog"
DATADOG_PASSWORD = "Datadog9000"
SCHEMA = "BENCH"
HOST = "localhost"
PORT = 39019


def connect(user: str, password: str, host: str = HOST, port: int = PORT):
    from hdbcli.dbapi import Connection as HanaConnection

    return HanaConnection(address=host, port=port, user=user, password=password)


def setup_user(cursor) -> None:
    try:
        cursor.execute(f'DROP USER {DATADOG_USER} CASCADE')
    except Exception:
        pass
    cursor.execute(f'CREATE RESTRICTED USER {DATADOG_USER} PASSWORD "{DATADOG_PASSWORD}"')
    cursor.execute(f'ALTER USER {DATADOG_USER} ENABLE CLIENT CONNECT')
    cursor.execute(f'ALTER USER {DATADOG_USER} DISABLE PASSWORD LIFETIME')
    cursor.execute(f'GRANT CATALOG READ TO {DATADOG_USER}')
    for view in (
        'SYS.M_DATABASE',
        'SYS.M_TABLES',
        'SYS.SCHEMAS',
        'SYS.TABLE_COLUMNS',
        'SYS.VIEWS',
        'SYS.VIEW_COLUMNS',
        'SYS.M_TABLE_STATISTICS',
    ):
        cursor.execute(f'GRANT SELECT ON {view} TO {DATADOG_USER}')


def setup_schema(cursor) -> None:
    try:
        cursor.execute(f'DROP SCHEMA {SCHEMA} CASCADE')
    except Exception:
        pass
    cursor.execute(f'CREATE SCHEMA {SCHEMA}')
    cursor.execute(f'GRANT SELECT ON SCHEMA {SCHEMA} TO {DATADOG_USER}')


def create_tables(conn, cursor) -> None:
    col_names = [f'C{i:04d}' for i in range(1, NUM_COLUMNS + 1)]
    col_defs = ', '.join(f'{name} INTEGER' for name in col_names)
    batch_size = 50
    for i in range(1, NUM_TABLES + 1):
        table = f'{SCHEMA}.T{i:04d}'
        cursor.execute(f'DROP TABLE {table} CASCADE') if False else None
        try:
            cursor.execute(f'DROP TABLE {table} CASCADE')
        except Exception:
            pass
        cursor.execute(f'CREATE COLUMN TABLE {table} ({col_defs})')
        if i % batch_size == 0:
            conn.commit()
            print(f'  created {i}/{NUM_TABLES} tables', flush=True)
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=HOST)
    parser.add_argument('--port', type=int, default=PORT)
    args = parser.parse_args()

    print(f'Connecting to {args.host}:{args.port} as {ADMIN_USER}...', flush=True)
    with closing(connect(ADMIN_USER, ADMIN_PASSWORD, host=args.host, port=args.port)) as conn:
        with closing(conn.cursor()) as cursor:
            print('Setting up monitoring user...', flush=True)
            setup_user(cursor)
            conn.commit()

            print('Setting up BENCH schema...', flush=True)
            setup_schema(cursor)
            conn.commit()

            print(f'Creating {NUM_TABLES} tables with {NUM_COLUMNS} columns each...', flush=True)
            print('(This may take several minutes. Lower NUM_COLUMNS/NUM_TABLES if HANA rejects them.)')
            create_tables(conn, cursor)

    print('Setup complete.', flush=True)


if __name__ == '__main__':
    sys.exit(main())
