# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import psycopg

from datadog_checks.base.utils.db.sql_commenter import add_sql_comment
from datadog_checks.postgres.encoding import decode_with_encodings

DD_QUERY_ATTRIBUTES = {
    'service': 'datadog-agent',
}


class BaseCommenterCursor:
    def __init__(self, *args, **kwargs):
        self.__attributes = DD_QUERY_ATTRIBUTES
        super().__init__(*args, **kwargs)

    def execute(self, query, params=None, ignore_query_metric=False, binary=False, prepare=None):
        '''
        When ignore is True, a /* DDIGNORE */ comment will be added to the query.
        This comment indicates that the query should be ignored in query metrics.
        '''
        query = add_sql_comment(query, prepand=True, **self.__attributes)
        if ignore_query_metric:
            query = '{} {}'.format('/* DDIGNORE */', query)
        return super().execute(query, params, binary=binary, prepare=prepare)


class CommenterCursor(BaseCommenterCursor, psycopg.ClientCursor):
    pass


class CommenterDictCursor(BaseCommenterCursor, psycopg.ClientCursor):
    pass


class DBMConnection(psycopg.Connection):
    """
    Extension of psycopg.Connection to keep a record of the original encoding.
    """

    def __init__(self, connection):
        self.__connection = connection
        self._original_encoding = self.__connection.info.encoding

    def __getattr__(self, attr):
        return getattr(self.__connection, attr)

    def __setattr__(self, attr, val):
        if attr == '_DBMConnection__connection':
            object.__setattr__(self, attr, val)

        return setattr(self.__connection, attr, val)

    @property
    def original_encoding(self):
        return self._original_encoding

    @original_encoding.setter
    def original_encoding(self, value):
        self._original_encoding = value

    def is_ascii(self):
        """
        Check if the original encoding is SQLASCII or ascii.
        """
        return self.original_encoding in ('SQLASCII', 'ascii')


class SQLASCIIBytesLoader(psycopg.adapt.Loader):
    """
    Custom loader for SQLASCII encoding.
    """

    encodings = ['utf-8']
    format = psycopg.pq.Format.BINARY

    def load(self, data):
        if type(data) is memoryview:
            # Convert memoryview to bytes
            data = data.tobytes()
        if type(data) is not bytes or data is None:
            return data
        print("loading bytes data", data)
        try:
            return decode_with_encodings(data, self.encodings)
        except:
            # Fallback to utf8 with replacement
            return data.decode('utf-8', errors='backslashreplace')


class SQLASCIITextLoader(psycopg.adapt.Loader):
    """
    Custom loader for SQLASCII encoding.
    """

    encodings = ['utf-8']
    format = psycopg.pq.Format.TEXT

    def load(self, data):
        if type(data) is memoryview:
            # Convert memoryview to bytes
            data = data.tobytes()
        if type(data) is not bytes or data is None:
            return data
        try:
            return decode_with_encodings(data, self.encodings)
        except:
            # Fallback to utf8 with replacement
            return data.decode('utf-8', errors='backslashreplace')
