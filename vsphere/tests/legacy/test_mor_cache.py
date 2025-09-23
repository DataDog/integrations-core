# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import pytest
from mock import MagicMock

from datadog_checks.vsphere.legacy.mor_cache import MorCache, MorNotFoundError


@pytest.fixture
def cache():
    return MorCache(MagicMock())


def test_contains(cache):
    cache._mor['foo_instance'] = {}
    assert cache.contains('foo_instance') is True
    assert cache.contains('foo') is False


def test_instance_size(cache):
    cache._mor['foo_instance'] = {}
    assert cache.instance_size('foo_instance') == 0
    cache._mor['foo_instance']['my_mor_name'] = None
    assert cache.instance_size('foo_instance') == 1
    with pytest.raises(KeyError):
        cache.instance_size('foo')


def test_set_mor(cache):
    cache._mor['foo_instance'] = {}
    cache.set_mor('foo_instance', 'mor_name', {'foo': 'bar'})
    assert 'foo' in cache._mor['foo_instance']['mor_name']
    # check the timestamp is set
    creation_time = cache._mor['foo_instance']['mor_name']['creation_time']
    assert creation_time > 0
    cache.set_mor('foo_instance', 'mor_name', {})
    time.sleep(0.1)  # be sure timestamp is different
    assert cache._mor['foo_instance']['mor_name']['creation_time'] > creation_time

    with pytest.raises(KeyError):
        cache.set_mor('foo', 'mor', {})


def test_get_mor(cache):
    with pytest.raises(KeyError):
        cache.get_mor('instance', 'mor_name')

    cache._mor['foo_instance'] = {'my_mor_name': {'foo': 'bar'}}

    assert cache.get_mor('foo_instance', 'my_mor_name')['foo'] == 'bar'

    with pytest.raises(MorNotFoundError):
        cache.get_mor('foo_instance', 'foo')


def test_set_metrics(cache):
    with pytest.raises(KeyError):
        cache.set_metrics('instance', 'mor_name', [])

    cache._mor['foo_instance'] = {'my_mor_name': {}}

    cache.set_metrics('foo_instance', 'my_mor_name', range(3))
    assert len(cache._mor['foo_instance']['my_mor_name']['metrics']) == 3

    with pytest.raises(MorNotFoundError):
        cache.set_metrics('foo_instance', 'foo', [])


def test_mors(cache):
    cache._mor['foo_instance'] = {}
    for i in range(9):
        # For the sake of this test, Mor name is `i` and Mor object is `None`
        cache._mor['foo_instance'][i] = None

    assert len(dict(cache.mors('foo_instance'))) == 9
    assert len(dict(cache.mors('foo'))) == 0


def test_mors_batch_realtime(cache):
    cache._mor['foo_instance'] = {}
    for i in range(9):
        # For the sake of this test, Mor name is `i` and Mor object is `None`
        cache._mor['foo_instance'][i] = {'mor_type': 'vm'}

    # input size is multiple of batch size
    steps = 0
    for mors in cache.mors_batch('foo_instance', 3):
        assert len(mors) == 3
        steps += 1
    assert steps == 3

    # batch size is smaller than the input size
    out = list(cache.mors_batch('foo_instance', 5))
    assert len(out) == 2
    assert len(out[0]) == 5
    assert len(out[1]) == 4

    # batch size is the same as the input size
    out = list(cache.mors_batch('foo_instance', 9))
    assert len(out) == 1
    assert len(out[0]) == 9

    # batch size is greater than the input size
    out = list(cache.mors_batch('foo_instance', 100))
    assert len(out) == 1
    assert len(out[0]) == 9


def test_mors_batch_historical(cache):
    cache._mor['foo_instance'] = {}
    for i in range(9):
        cache._mor['foo_instance'][i] = {'mor_type': 'datastore', 'metrics': range(5)}

    # input size is multiple of batch size
    steps = 0
    for mors in cache.mors_batch('foo_instance', 3):
        assert len(mors) == 3
        steps += 1
    assert steps == 3

    # batch size is smaller than the input size
    out = list(cache.mors_batch('foo_instance', 5))
    assert len(out) == 2
    assert len(out[0]) == 5
    assert len(out[1]) == 4

    # batch size is the same as the input size
    out = list(cache.mors_batch('foo_instance', 9))
    assert len(out) == 1
    assert len(out[0]) == 9

    # batch size is greater than the input size
    out = list(cache.mors_batch('foo_instance', 100))
    assert len(out) == 1
    assert len(out[0]) == 9

    # input size is multiple of batch size
    steps = 0
    for mors in cache.mors_batch('foo_instance', 3, max_historical_metrics=16):
        assert len(mors) == 3
        assert sum([len(mors[m]['metrics']) for m in mors]) == 15
        steps += 1
    assert steps == 3

    steps = 0
    for mors in cache.mors_batch('foo_instance', 3, max_historical_metrics=9):
        assert len(mors) == 1
        assert sum([len(mors[m]['metrics']) for m in mors]) == 5
        steps += 1
    assert steps == 9

    steps = 0
    for mors in cache.mors_batch('foo_instance', 3, max_historical_metrics=6):
        assert len(mors) == 1
        assert sum([len(mors[m]['metrics']) for m in mors]) == 5
        steps += 1
    assert steps == 9

    steps = 0
    for _ in cache.mors_batch('foo_instance', 3, max_historical_metrics=4):
        steps += 1
    assert steps == 0


def test_purge(cache):
    cache._mor['foo_instance'] = {}
    for i in range(3):
        # set last access to 0, these will be purged
        cache._mor['foo_instance'][i] = {'creation_time': 0}
    # this entry should stay
    cache._mor['foo_instance']['hero'] = {'creation_time': time.time()}
    # purge items older than 60 seconds
    cache.purge('foo_instance', 60)
    assert len(cache._mor['foo_instance']) == 1
    assert 'hero' in cache._mor['foo_instance']
