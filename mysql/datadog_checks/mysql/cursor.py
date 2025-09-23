# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pymysql

from datadog_checks.base.utils.db.sql_commenter import add_sql_comment

DD_QUERY_ATTRIBUTES = {
    'service': 'datadog-agent',
}


class BaseCommenterCursor:
    def __init__(self, *args, **kwargs):
        self.__attributes = DD_QUERY_ATTRIBUTES
        super().__init__(*args, **kwargs)

    def execute(self, query, args=None):
        query = add_sql_comment(query, prepand=True, **self.__attributes)
        return super().execute(query, args)


class CommenterCursor(BaseCommenterCursor, pymysql.cursors.Cursor):
    pass


class CommenterDictCursor(BaseCommenterCursor, pymysql.cursors.DictCursor):
    pass


class CommenterSSCursor(BaseCommenterCursor, pymysql.cursors.SSCursor):
    pass


class CommenterSSDictCursor(BaseCommenterCursor, pymysql.cursors.SSDictCursor):
    pass
