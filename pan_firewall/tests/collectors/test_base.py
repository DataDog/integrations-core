# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.collectors.base import read_each
from datadog_checks.pan_firewall.errors import PanosApiError, PanosAuthError, PanosError, PanosUnreachable

pytestmark = pytest.mark.unit


def reader(**failures):
    """A read that answers `item.upper()`, or raises the exception `failures[item]`."""

    def read(item):
        if item in failures:
            raise failures[item]
        return item.upper()

    return read


def test_failing_item_is_skipped_and_reported():
    errors = []

    answers = list(read_each(['a', 'b'], reader(a=PanosApiError('17', 'no')), lambda item, e: errors.append(item)))

    assert answers == [('b', 'B')]
    assert errors == ['a']


def test_raises_the_last_error_when_no_item_answered():
    last = PanosError('bad answer')

    with pytest.raises(PanosError) as raised:
        list(read_each(['a', 'b'], reader(a=PanosApiError('17', 'no'), b=last), lambda item, e: None))

    assert raised.value is last


def test_no_items_is_not_a_failure():
    assert list(read_each([], reader(), lambda item, e: None)) == []


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(PanosAuthError('403', 'Invalid credentials.'), id='auth'),
        pytest.param(PanosUnreachable('timed out'), id='unreachable'),
    ],
)
def test_auth_and_connection_errors_propagate_at_once(error):
    errors = []

    with pytest.raises(type(error)):
        list(read_each(['a', 'b'], reader(a=error), lambda item, e: errors.append(item)))

    assert errors == []
