# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.db.sql_commenter import add_sql_comment

DD_QUERY_ATTRIBUTES = {
    'service': 'datadog-agent',
}


class CommenterCursorWrapper:
    '''
    Simple wrapper around a cursor that prepands a comment before executing each query

    Why not extend pyodbc.Cursor or adodbapi.Cursor?
    - we want to be able to use this with any cursor, not just a specific one.
    - classes that are implemented in C or are part of a module that does not support subclassing in this way.
    i.e. class CommenterCursor(pyodbc.Cursor) is not possible because pyodbc.Cursor is implemented in C.
    '''

    def __init__(self, cursor):
        self.__attributes = DD_QUERY_ATTRIBUTES
        self.__cursor = cursor
        self._columns = None

    def execute(self, query, *params):
        query = add_sql_comment(query, True, **self.__attributes)
        self._columns = None
        return self.__cursor.execute(query, *params)

    def __getattr__(self, item):
        # This method ensures that any other attributes or methods not explicitly defined here
        # are passed through to the underlying cursor.
        return getattr(self.__cursor, item)

    def _get_columns(self):
        if self._columns is None:
            self._columns = [i[0] for i in self.__cursor.description]
        return self._columns

    def fetchall_dict(self):
        columns = self._get_columns()
        return [dict(zip(columns, row)) for row in self.__cursor.fetchall()]

    def fetchone_dict(self):
        row = self.__cursor.fetchone()
        if row is None:
            return None
        return dict(zip(self._get_columns(), row))
