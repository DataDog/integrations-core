# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from collections import OrderedDict
from typing import Any

import mock
import pytest
from six import PY3

from datadog_checks.base import AgentCheck
from datadog_checks.base import __version__ as base_package_version
from datadog_checks.base import to_native_string
from datadog_checks.base.checks.base import datadog_agent
from datadog_checks.base.utils.weakref import WeakDeque


class Foo(object):
    def __init__(self, val):
        self.val = val


def test_weak_deque_append_del_pop():
    a,b,c = Foo("a"), Foo("b"), Foo("c")

    deq = WeakDeque([a])
    deq.append(b)
    deq.append(c)

    del b

    assert len(deq) == 3
    assert deq.pop().val == "c"
    assert deq.pop().val == "a"
    assert len(deq) == 0


def test_weak_deque_appendleft():
    a,b,c = Foo("a"), Foo("b"), Foo("c")

    deq = WeakDeque([a])
    deq.appendleft(b)
    deq.appendleft(c)

    assert deq.pop().val == "a"
    assert deq.pop().val == "b"
    assert deq.pop().val == "c"


def test_weak_deque_extend():
    a,b,c = Foo("a"), Foo("b"), Foo("c")

    deq = WeakDeque([a])
    deq.extend([b, c])

    assert deq.pop().val == "c"
    assert deq.pop().val == "b"
    assert deq.pop().val == "a"


def test_weak_deque_extendleft():
    a,b,c = Foo("a"), Foo("b"), Foo("c")

    deq = WeakDeque([a])
    deq.extendleft([b, c])

    assert deq.popleft().val == "c"
    assert deq.popleft().val == "b"
    assert deq.popleft().val == "a"


def test_weak_deque_popleft():
    a,b,c = Foo("a"), Foo("b"), Foo("c")

    deq = WeakDeque([a])
    deq.append(b)
    deq.append(c)

    assert deq.popleft().val == "a"
    assert deq.popleft().val == "b"
    assert deq.popleft().val == "c"




