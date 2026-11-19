# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import psycopg

from datadog_checks.base.utils.db.sql_commenter import add_sql_comment
from datadog_checks.postgres.encoding import decode_with_encodings
from datadog_checks.postgres.util import DDIGNORE_COMMENT

DD_QUERY_ATTRIBUTES = {
    'service': 'datadog-agent',
}


def _append_ddignore_comment(query):
    # pg_stat_statements drops anything after the terminating semicolon, so the marker goes before it.
    query = query.rstrip()
    if query.endswith(';'):
        return '{} {};'.format(query[:-1].rstrip(), DDIGNORE_COMMENT)
    return '{} {}'.format(query, DDIGNORE_COMMENT)


class BaseCommenterCursor:
    def __init__(self, *args, **kwargs):
        self.__attributes = DD_QUERY_ATTRIBUTES
        super().__init__(*args, **kwargs)

    def execute(self, query, params=None, ignore_query_metric=False, binary=False, prepare=None):
        '''
        When ignore is True, a DDIGNORE comment will be added to the query.
        This comment indicates that the query should be ignored in query metrics.

        The DDIGNORE comment is appended rather than prepended: Postgres 18 strips leading comments from the
        text stored in pg_stat_statements, which would hide a leading marker from the query metrics filters.
        '''
        query = add_sql_comment(query, prepand=True, **self.__attributes)
        if ignore_query_metric:
            query = _append_ddignore_comment(query)
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
