# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.containers import hash_mutable, hash_mutable_stable

COMPLEX_OBJECT = {
    'url': 'http://localhost:9090/metrics',
    'tags': ['test:tag', 'env:dev'],
    'port': 9090,
    'options': {'timeout': 5, 'retries': 3},
    'none_value': None,
    123: 'integer_key',
}


@pytest.mark.parametrize(
    'val1, val2',
    [
        pytest.param({'a': 1, 'b': 2}, {'b': 2, 'a': 1}, id='dict-same-items-different-order'),
        pytest.param([1, 2, 3], (1, 2, 3), id='list-tuple-same-items'),
        pytest.param({1, 2, 3}, {3, 2, 1}, id='set-same-items-different-order'),
        pytest.param({1, 2, 3}, frozenset([1, 2, 3]), id='set-frozenset-same-items'),
        pytest.param([1, 2], [2, 1], id='list-same-items-different-order'),
        pytest.param((1, 2), (2, 1), id='tuple-same-items-different-order'),
        pytest.param([{'a': 1}, {'b': 2}], [{'b': 2}, {'a': 1}], id='list-of-dicts-different-order'),
        pytest.param(('a', 1), (1, 'a'), id='tuple-mixed-types-different-order'),
        pytest.param([1, "a", None, 5.5], [5.5, None, "a", 1], id='list-multiple-mixed-types-different-order'),
        pytest.param([{'a': 1}, None], [None, {'a': 1}], id='list-with-dict-and-none-different-order'),
        pytest.param([{'a': 1, 'b': None}], [{'a': 1, 'b': None}], id='list-with-dict-with-none-value'),
    ],
)
def test_hash_mutable_equal(val1, val2):
    """
    Test that hash_mutable produces the same hash for collections with the same items,
    regardless of order or container type (list, tuple, set, dict).
    """
    assert hash_mutable(val1) == hash_mutable(val2)


@pytest.mark.parametrize(
    'val1, val2',
    [
        pytest.param([1, 2], [1, 2, 3], id='lists-different-items'),
        pytest.param({'a': 1}, {'a': 2}, id='dicts-different-items'),
    ],
)
def test_hash_mutable_unequal(val1, val2):
    """
    Test that hash_mutable produces different hashes for collections with different items.
    """
    assert hash_mutable(val1) != hash_mutable(val2)


@pytest.mark.parametrize(
    'val',
    [
        pytest.param(123, id='integer'),
        pytest.param("string", id='string'),
        pytest.param(None, id='none'),
    ],
)
def test_hash_mutable_hashable_types(val):
    """
    Test that for hashable types, hash_mutable is the same as hash().
    """
    assert hash_mutable(val) == hash(val)


# Tests for the hash_mutable_stable just ensure that the hash is always the same
# No need to cover all usecases since internally we use the same logic as with hash_mutable


def test_hash_mutable_stable_default_length():
    expected = "3f5c577e87bc8144e1cd3a622fa5a053"
    assert hash_mutable_stable(COMPLEX_OBJECT) == expected


@pytest.mark.parametrize(
    'length, expected',
    [
        pytest.param(16, "3f5c577e87bc8144", id='length-16'),
        pytest.param(8, "3f5c577e", id='length-8'),
    ],
)
def test_hash_mutable_stable_custom_length(length, expected):
    """Test custom lengths."""
    assert hash_mutable_stable(COMPLEX_OBJECT, length=length) == expected
