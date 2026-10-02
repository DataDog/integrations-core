# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fake pymysql connections for the Data Observability task and query session tests."""

import pymysql

MYSQL_8 = ('8.0.36', 'MySQL Community Server - GPL')


class FakeConnection:
    """
    Stands in for a pymysql connection. `results` maps SQL text to `(columns, rows)`, to an
    exception to raise, or to a callable taking the connection that does either. Any other
    statement succeeds without a result set.
    """

    def __init__(self, results=None, version=MYSQL_8):
        self.results = results or {}
        self.version = version
        self.open = True
        self.executed = []
        self.fetch_sizes = []
        self.cursor_classes = []

    def cursor(self, cursor_class=None):
        self.cursor_classes.append(cursor_class)
        return FakeCursor(self)

    def close(self):
        if not self.open:
            raise pymysql.err.Error('Already closed')
        self.open = False


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None
        self.rows = []
        self.fetched = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def execute(self, sql, args=None):
        self.conn.executed.append(sql if args is None else (sql, args))
        self.description, self.rows, self.fetched = None, [], 0
        if sql.startswith('SELECT @@version'):
            self.description, self.rows = [('@@version',), ('@@version_comment',)], [self.conn.version]
            return
        result = self.conn.results.get(sql)
        if callable(result):
            result = result(self.conn)
        if isinstance(result, BaseException):
            raise result
        if result is not None:
            columns, self.rows = result
            self.description = [(column,) for column in columns]

    def fetchone(self):
        return self.rows[0]

    def fetchmany(self, size):
        self.conn.fetch_sizes.append(size)
        batch = self.rows[self.fetched : self.fetched + size]
        self.fetched += len(batch)
        return batch

    def close(self):
        pass
