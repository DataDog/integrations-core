# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from hdbcli.dbapi import OperationalError  # noqa: F401


class QueryExecutionError(Exception):
    def __init__(self, message, source):
        super(QueryExecutionError, self).__init__(message)
        self.source = source
