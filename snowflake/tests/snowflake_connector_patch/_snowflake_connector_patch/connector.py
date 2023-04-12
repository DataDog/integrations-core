# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import requests

from . import tables

TABLE_PATTERN = re.compile(r'from (\w+)')


def connect(*args, **kwargs):
    # Check for:
    # https://github.com/snowflakedb/snowflake-connector-python/issues/324
    response = requests.get('https://www.google.com')
    response.raise_for_status()

    return Connection(*args, **kwargs)


class Connection(object):
    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__()
        self.schema = kwargs.get('schema')

    def cursor(self, *args, **kwargs):
        return Cursor(schema=self.schema, *args, **kwargs)  # noqa: B026

    def close(self):
        pass


class Cursor(object):
    def __init__(self, *args, **kwargs):
        super(Cursor, self).__init__()
        self.schema = kwargs.get('schema')
        self.__data = []

    @property
    def rowcount(self):
        return len(self.__data)

    def execute(self, query):
        match = TABLE_PATTERN.search(query)
        if match:
            table_name = match.group(1)
            table_prefix = ''
            if self.schema == 'ORGANIZATION_USAGE':
                table_prefix = 'ORGANIZATION_'
            table_attr = "{}{}".format(table_prefix, table_name)
            self.__data = getattr(tables, table_attr, [])
        elif query == 'select current_version();':
            self.__data = [('4.30.2',)]
        else:
            self.__data = []

    def fetchall(self):
        return self.__data

    def close(self):
        pass
