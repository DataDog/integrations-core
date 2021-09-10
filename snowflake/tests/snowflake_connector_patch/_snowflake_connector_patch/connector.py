# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from . import tables

TABLE_PATTERN = re.compile(r'from (\w+)')


def connect(*args, **kwargs):
    return Connection(*args, **kwargs)


class Connection(object):
    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__()

    def cursor(self, *args, **kwargs):
        return Cursor(*args, **kwargs)

    def close(self):
        pass


class Cursor(object):
    def __init__(self, *args, **kwargs):
        super(Cursor, self).__init__()

        self.__data = []

    @property
    def rowcount(self):
        return len(self.__data)

    def execute(self, query):
        match = TABLE_PATTERN.search(query)
        if match:
            table_name = match.group(1)
            self.__data = getattr(tables, table_name, [])
        elif query == 'select current_version();':
            self.__data = [('4.30.2',)]
        else:
            self.__data = []

    def fetchall(self):
        return self.__data

    def close(self):
        pass
