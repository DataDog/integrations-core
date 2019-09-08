# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class QueryExecutionError(Exception):
    def __init__(self, message, source):
        super(QueryExecutionError, self).__init__(message)
        self.source = source
