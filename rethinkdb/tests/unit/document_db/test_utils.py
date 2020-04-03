# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import pytest

from datadog_checks.rethinkdb.document_db.utils import dotted_join, lookup_dotted

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'value, output',
    [
        ((), ''),
        (('foo',), 'foo'),
        (('foo', 'bar'), 'foo.bar'),
        (('foo', 'bar', 'baz'), 'foo.bar.baz'),
        (('foo', 'bar', ''), 'foo.bar'),
        (('foo', '', 'baz'), 'foo.baz'),
        (('', 'bar', 'baz'), 'bar.baz'),
    ],
)
def test_dotted_join(value, output):
    # type: (tuple, str) -> None
    assert dotted_join(value) == output


@pytest.mark.parametrize(
    'dct, path, output',
    [
        ({}, '', {}),
        ({'tables': 10}, 'tables', 10),
        ({'tables': {'reads_per_sec': 500}}, 'tables.reads_per_sec', 500),
        ({'tables': {'all': ['heroes']}}, 'tables.all', ['heroes']),
        ({}, '', {}),
    ],
)
def test_lookup_dotted(dct, path, output):
    # type: (dict, str, Any) -> None
    assert lookup_dotted(dct, path) == output


@pytest.mark.parametrize(
    'value, path',
    [
        pytest.param([], 'test', id='root-not-a-mapping'),
        pytest.param(True, 'test', id='root-not-a-mapping'),
        pytest.param({'tables': 10}, 'tables.total', id='node-not-a-mapping'),
        pytest.param({}, 'unknown', id='key-does-not-exist'),
        pytest.param({'tables': {'total': 10}}, 'tables.unknown', id='key-does-not-exist'),
        pytest.param({'tables.total': 10}, 'tables.total', id='dotted-key-not-supported'),
    ],
)
def test_lookup_dotted_invalid(value, path):
    # type: (Any, str) -> None
    with pytest.raises(ValueError):
        lookup_dotted(value, path)
