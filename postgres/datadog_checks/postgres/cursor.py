# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

import psycopg

from datadog_checks.base.utils.db.sql_commenter import add_sql_comment
from datadog_checks.postgres.encoding import decode_with_encodings
from datadog_checks.postgres.util import DDIGNORE_COMMENT

log = logging.getLogger(__name__)

DD_QUERY_ATTRIBUTES = {
    'service': 'datadog-agent',
}


# Postgres 18 strips leading comments from the text stored in pg_stat_statements.
LEADING_COMMENTS_STRIPPED_SERVER_VERSION_NUM = 180000


def _append_ddignore_comment(query):
    # pg_stat_statements drops anything after the terminating semicolon, so the marker goes before it.
    query = query.rstrip()
    if query.endswith(';'):
        return '{} {};'.format(query[:-1].rstrip(), DDIGNORE_COMMENT)
    return '{} {}'.format(query, DDIGNORE_COMMENT)


def _stores_leading_comments(cursor):
    """
    Whether the server keeps leading comments in the text stored in pg_stat_statements.

    This runs before every query, so it must never fail one. The version is read from the state libpq
    holds for the connection, with no round trip. When it cannot be read, for example on a closed
    connection, fall back to leading comments and let the query itself report the real error.
    """
    try:
        return cursor.connection.info.server_version < LEADING_COMMENTS_STRIPPED_SERVER_VERSION_NUM
    except (psycopg.Error, AttributeError, TypeError) as e:
        log.debug("Could not read the server version to place query comments, using leading comments: %s", e)
        return True


def _add_comments(query, attributes, ignore_query_metric, leading):
    """
    Add the service comment and, when ignore_query_metric is set, the DDIGNORE marker to the query.

    Leading comments are kept on versions that store them in pg_stat_statements. Elsewhere they are
    appended, since they would otherwise be missing from the stored text.
    """
    if leading:
        query = add_sql_comment(query, prepand=True, **attributes)
        return '{} {}'.format(DDIGNORE_COMMENT, query) if ignore_query_metric else query
    query = add_sql_comment(query, prepand=False, **attributes)
    return _append_ddignore_comment(query) if ignore_query_metric else query


class BaseCommenterCursor:
    def __init__(self, *args, **kwargs):
        self.__attributes = DD_QUERY_ATTRIBUTES
        super().__init__(*args, **kwargs)

    def execute(self, query, params=None, ignore_query_metric=False, binary=False, prepare=None):
        '''
        When ignore is True, a DDIGNORE comment will be added to the query.
        This comment indicates that the query should be ignored in query metrics.
        '''
        query = _add_comments(query, self.__attributes, ignore_query_metric, _stores_leading_comments(self))
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
