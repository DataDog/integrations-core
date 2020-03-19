# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime as dt

import pytest

from datadog_checks.rethinkdb.document_db.utils import dotted_join, lookup_dotted, to_timestamp

pytestmark = pytest.mark.unit


def test_dotted_join():
    # type: () -> None
    assert dotted_join(()) == ''
    assert dotted_join(('foo',)) == 'foo'
    assert dotted_join(('foo', 'bar')) == 'foo.bar'
    assert dotted_join(('foo', 'bar', 'baz')) == 'foo.bar.baz'
    assert dotted_join(('foo', 'bar', '')) == 'foo.bar'
    assert dotted_join(('foo', '', 'baz')) == 'foo.baz'
    assert dotted_join(('', 'bar', 'baz')) == 'bar.baz'


def test_to_timestamp():
    # type: () -> None
    datetime = dt.datetime(year=2020, month=1, day=1, hour=3, minute=45, second=0)
    assert to_timestamp(datetime) == 1577846700.0


def test_lookup_dotted():
    # type: () -> None
    assert lookup_dotted({}, '') == {}
    assert lookup_dotted({'tables': 10}, 'tables') == 10
    assert lookup_dotted({'tables': {'reads_per_sec': 500}}, 'tables.reads_per_sec') == 500
    assert lookup_dotted({'tables': {'all': ['heroes']}}, 'tables.all') == ['heroes']

    with pytest.raises(ValueError):
        lookup_dotted([], 'test')  # type: ignore

    with pytest.raises(ValueError):
        lookup_dotted(True, 'test')  # type: ignore

    with pytest.raises(ValueError):
        lookup_dotted({'tables': 10}, 'tables.total')

    with pytest.raises(ValueError):
        lookup_dotted({'tables': {'total': 10}}, 'tables.unknown')

    with pytest.raises(ValueError):
        # Dotted keys are not supported.
        lookup_dotted({'tables.total': 10}, 'tables.total')
