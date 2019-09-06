# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class QueryExecutionError(Exception):
    def __init__(self, message, query_class):
        super(QueryExecutionError, self).__init__(message)
        self.query_class = query_class
