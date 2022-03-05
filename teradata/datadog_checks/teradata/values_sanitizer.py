# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.teradata.queries import DB_SPACE


class TeradataSanitizerException(Exception):
    pass


def get_row_sanitizer(query):
    sanitizers = {DB_SPACE['query']: _sanitize_row}
    return sanitizers.get(query, _sanitizer_method)


def _sanitizer_method(row):
    return row


def _sanitize_row(row):
    if len(row) != 3:
        raise TeradataSanitizerException(
            "row {} for query 'DB_SPACE' should have 3 elements, found {}".format(row, len(row))
        )
    return _sanitize_tags(row[0]), _sanitize_tags(row[1]), _sanitize_tags(row[2])


def _sanitize_tags(value):
    if type(value) == str:
        if value == '':
            return value
        else:
            return value.strip()
    else:
        return value
