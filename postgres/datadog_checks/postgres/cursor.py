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


class SQLASCIITextLoader(psycopg.adapt.Loader):
    """
    Custom loader for SQLASCII encoding.
    """

    encodings = ['utf-8']
    format = psycopg.pq.Format.TEXT

    def load(self, data):
        if data is None:
            return data
        if isinstance(data, memoryview):
            # Convert memoryview to bytes
            data = data.tobytes()
        if not isinstance(data, bytes):
            return data
        try:
            return decode_with_encodings(data, self.encodings)
        except Exception:
            # Fallback to utf8 with replacement
            return data.decode('utf-8', errors='backslashreplace')
