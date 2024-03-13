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

    def execute(self, query, *params):
        query = add_sql_comment(query, True, **self.__attributes)
        return self.__cursor.execute(query, *params)

    def __getattr__(self, item):
        # This method ensures that any other attributes or methods not explicitly defined here
        # are passed through to the underlying cursor.
        return getattr(self.__cursor, item)
