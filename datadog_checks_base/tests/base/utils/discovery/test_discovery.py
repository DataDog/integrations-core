# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import mock
import pytest

from datadog_checks.base.utils.discovery import Discovery


def test_include_empty():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items)
    assert list(d.get_items()) == []
    assert mock_get_items.call_count == 1


@pytest.mark.parametrize(
    'pattern',
    [
        pytest.param(
            'a.*',
            id='with string',
        ),
        pytest.param(
            re.compile('a.*'),
            id='with compiled pattern',
        ),
    ],
)
def test_include_not_empty(pattern):
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, include={pattern: None})
    assert list(d.get_items()) == [(pattern, 'a', 'a', None)]
    assert mock_get_items.call_count == 1


def test_include_processed_in_order():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, include={'c.*': {'value': 5}, 'a.*': {'value': 10}})
    assert list(d.get_items()) == [('c.*', 'c', 'c', {'value': 5}), ('a.*', 'a', 'a', {'value': 10})]
    assert mock_get_items.call_count == 1


def test_exclude_and_include_intersection_is_empty():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, include={'a.*': None}, exclude=['b.*'])
    assert list(d.get_items()) == [('a.*', 'a', 'a', None)]
    assert mock_get_items.call_count == 1


def test_exclude_is_subset_of_include():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, include={'.*': None}, exclude=['b.*'])
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
        ('.*', 'e', 'e', None),
        ('.*', 'f', 'f', None),
        ('.*', 'g', 'g', None),
    ]
    assert mock_get_items.call_count == 1


def test_exclude_is_equals_to_include():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(limit=10, include={'b.*': None}, exclude=['b.*'], interval=0, get_items_func=mock_get_items)
    assert list(d.get_items()) == []
    assert mock_get_items.call_count == 1


def test_limit_zero():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=0, include={'.*': None})
    assert list(d.get_items()) == []
    assert mock_get_items.call_count == 1


def test_limit_none():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=None, include={'.*': None})
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'b', 'b', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
        ('.*', 'e', 'e', None),
        ('.*', 'f', 'f', None),
        ('.*', 'g', 'g', None),
    ]
    assert mock_get_items.call_count == 1


def test_limit_greater_than_zero():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=5, include={'.*': {'value': 5}})
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', {'value': 5}),
        ('.*', 'b', 'b', {'value': 5}),
        ('.*', 'c', 'c', {'value': 5}),
        ('.*', 'd', 'd', {'value': 5}),
        ('.*', 'e', 'e', {'value': 5}),
    ]
    assert mock_get_items.call_count == 1


def test_limit_greater_than_items_len():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=10, include={'.*': None})
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'b', 'b', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
        ('.*', 'e', 'e', None),
        ('.*', 'f', 'f', None),
        ('.*', 'g', 'g', None),
    ]
    assert mock_get_items.call_count == 1


def test_interval_none_two_calls_to_get_items_func():
    mock_get_items = mock.Mock(side_effect=[['a', 'b'], ['a', 'b', 'c', 'd']])
    d = Discovery(mock_get_items, include={'.*': None}, interval=None)
    assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'b', 'b', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
    ]
    assert mock_get_items.call_count == 2


def test_interval_zero_two_calls_to_get_items_func():
    mock_get_items = mock.Mock(side_effect=[['a', 'b'], ['a', 'b', 'c', 'd']])
    d = Discovery(mock_get_items, include={'.*': None})
    assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'b', 'b', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
    ]
    assert mock_get_items.call_count == 2


def test_interval_not_exceeded():
    mock_get_items = mock.Mock(side_effect=[['a', 'b'], ['a', 'b', 'c', 'd']])
    with mock.patch('time.time', side_effect=[100, 120]):
        d = Discovery(mock_get_items, include={'.*': None}, interval=60)
        assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
        assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
        assert mock_get_items.call_count == 1


def test_interval_exceeded():
    mock_get_items = mock.Mock(side_effect=[['a', 'b'], ['a', 'b', 'c', 'd']])
    with mock.patch('time.time', side_effect=[100, 168, 168]):
        d = Discovery(mock_get_items, include={'.*': None}, interval=60)
        assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
        assert list(d.get_items()) == [
            ('.*', 'a', 'a', None),
            ('.*', 'b', 'b', None),
            ('.*', 'c', 'c', None),
            ('.*', 'd', 'd', None),
        ]
        assert mock_get_items.call_count == 2


def test_key_in_items():
    mock_get_items = mock.Mock(return_value=[{'key': 'a', 'value': 75}, {'key': 'b', 'value': 89}])
    d = Discovery(mock_get_items, include={'a.*': {'filter': 'xxxx'}}, key=lambda item: item['key'])
    assert list(d.get_items()) == [('a.*', 'a', {'key': 'a', 'value': 75}, {'filter': 'xxxx'})]
    assert mock_get_items.call_count == 1
