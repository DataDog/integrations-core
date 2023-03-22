# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import AnyStr, Callable, Sequence, Union  # noqa: F401

from datadog_checks.singlestore.queries import AGGREGATORS, MV_GLOBAL_STATUS


class SingleStoreCleaningException(Exception):
    pass


UNITS = {
    'GB': 1e9,
    'MB': 1e6,
    'KB': 1e3,
    'Bytes': 1,
    'ms': 1e-3,
    'ns': 1e-9,
    'units': 1,
}


def get_row_cleaner(query):
    # type: (AnyStr) -> Callable[[Sequence], Sequence]
    cleaners = {MV_GLOBAL_STATUS['query']: _clean_mv_global_status, AGGREGATORS['query']: _clean_aggregators}
    return cleaners.get(query, _identity_method)


def _identity_method(row):
    # type: (Sequence) -> Sequence
    return row


def _clean_units(value):
    # type: (str) -> Union[float, str]
    # Possible variable_value formats:
    # - "12.4"
    # - "120.1 MB"
    # - "12 ms"
    # - "267.883 (+267.883) MB"
    if value == '':
        return 0.0

    components = value.split(' ')
    scale = UNITS[components[-1]]
    return float(components[0]) * scale


def _clean_mv_global_status(row):
    # type: (Sequence) -> Sequence
    if len(row) != 6:
        raise SingleStoreCleaningException(
            "row {} for query 'MV_GLOBAL_STATUS' should have 6 elements, found {}".format(row, len(row))
        )
    return row[0], row[1], row[2], row[3], row[4], _clean_units(row[5])


def _clean_aggregators(row):
    # type: (Sequence) -> Sequence
    if len(row) != 6:
        raise SingleStoreCleaningException(
            "row {} for query 'AGGREGATORS' should have 6 elements, found {}".format(row, len(row))
        )
    return row[0], row[1], row[2], row[3], row[4], _clean_units(row[5])
