# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
import time

import pytest

from datadog_checks.base.utils.concurrency.limiter import ConditionLimiter


def test_no_condition():
    class Limiter(ConditionLimiter):
        pass

    with pytest.raises(NotImplementedError):
        Limiter().check_condition('foo')


def test_default_limit():
    class Limiter(ConditionLimiter):
        def condition(self, *args, **kwargs):
            return True

    limiter = Limiter()
    assert not limiter.limit_reached()

    assert limiter.check_condition('foo')
    assert limiter.limit_reached()

    assert limiter.check_condition('foo')
    assert not limiter.check_condition('bar')


def test_default_if_no_limit():
    class Limiter(ConditionLimiter):
        def condition(self, *args, **kwargs):
            return True

    limiter = Limiter()
    assert not limiter.limit_reached()

    assert limiter.check_condition('foo')
    assert limiter.limit_reached()

    assert limiter.check_condition('foo')
    assert not limiter.check_condition('bar')


def test_specific_limit():
    class Limiter(ConditionLimiter):
        def condition(self, *args, **kwargs):
            return True

    limiter = Limiter(2)
    assert not limiter.limit_reached()

    assert limiter.check_condition('foo')
    assert not limiter.limit_reached()

    assert limiter.check_condition('bar')
    assert limiter.limit_reached()

    assert limiter.check_condition('foo')
    assert limiter.check_condition('bar')
    assert not limiter.check_condition('baz')


def test_removal():
    class Limiter(ConditionLimiter):
        def condition(self, *args, **kwargs):
            return True

    limiter = Limiter(2)
    assert not limiter.limit_reached()

    assert limiter.check_condition('foo')
    assert not limiter.limit_reached()

    assert limiter.check_condition('bar')
    assert limiter.limit_reached()

    assert limiter.check_condition('foo')
    assert limiter.check_condition('bar')
    assert not limiter.check_condition('baz')

    limiter.remove('foo')
    assert not limiter.limit_reached()

    assert limiter.check_condition('baz')
    assert limiter.limit_reached()

    assert limiter.check_condition('bar')
    assert limiter.check_condition('baz')
    assert not limiter.check_condition('foo')


def test_arguments():
    class Limiter(ConditionLimiter):
        def condition(self, arg, kwarg=None):
            return arg == 'bar' and kwarg == 'baz'

    limiter = Limiter()
    assert not limiter.limit_reached()

    assert not limiter.check_condition('foo', 'bar')
    assert not limiter.limit_reached()

    assert limiter.check_condition('foo', 'bar', kwarg='baz')
    assert limiter.limit_reached()

    assert limiter.check_condition('foo', 'bar', kwarg='baz')
    assert not limiter.check_condition('foobar', 'bar', kwarg='baz')


def test_locking():
    class Limiter(ConditionLimiter):
        def __init__(self, *args, **kwargs):
            super(Limiter, self).__init__(*args, **kwargs)
            self.__count = 0

        def condition(self, *args, **kwargs):
            if self.__count > 0:
                raise Exception('too many calls')

            time.sleep(0.5)
            self.__count += 1
            return True

    limiter = Limiter()

    def gen(identifier):
        def func():
            limiter.check_condition(identifier)

        return func

    threads = (threading.Thread(target=gen('foo')), threading.Thread(target=gen('bar')))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert limiter.limit_reached()

    assert {limiter.check_condition('foo'), limiter.check_condition('bar')} == {True, False}
