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

    A row may also be an exception, or a callable taking the connection that returns one: the read
    that reaches it raises it, as when the server sends an error packet or the connection drops
    mid-result. Like pymysql, that read loses the rows it had read before the error.
    """

    def __init__(self, results=None, version=MYSQL_8):
        self.results = results or {}
        self.version = version
        self.open = True
        self.executed = []
        self.fetch_sizes = []
        self.cursor_classes = []
        # Called with no arguments at every fetchmany(), so tests can act or record state mid-read.
        self.on_fetch = None
        # Set when a cursor is closed with rows left unread, which pymysql would read and discard.
        self.drained = False
        # Like the server, results stop at the session's sql_select_limit.
        self.select_limit = None

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
        if sql == 'SET SESSION sql_select_limit = %s':
            (self.conn.select_limit,) = args
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
            if self.conn.select_limit is not None:
                self.rows = self.rows[: self.conn.select_limit]
            self.description = [(column,) for column in columns]

    def fetchone(self):
        row = self.rows[self.fetched]
        self.fetched += 1
        return row

    def fetchmany(self, size):
        self.conn.fetch_sizes.append(size)
        if self.conn.on_fetch is not None:
            self.conn.on_fetch()
        batch = self.rows[self.fetched : self.fetched + size]
        for row in batch:
            if not isinstance(row, tuple):
                # Like pymysql after an error packet or a lost connection, the result is over.
                self.fetched = len(self.rows)
                raise row(self.conn) if callable(row) else row
        self.fetched += len(batch)
        return batch

    def close(self):
        if self.fetched < len(self.rows):
            self.conn.drained = True
