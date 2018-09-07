# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.vsphere.objects_queue import ObjectsQueue


@pytest.fixture
def q():
    return ObjectsQueue()


def test_objects_queue_init(q):
    assert len(q._objects_queue) == 0


def test_objects_queue_fill(q):
    q.fill('foo', {
        'type_foo': [],
        'type_bar': [-99],
    })
    assert len(q._objects_queue) == 1
    assert len(q._objects_queue['foo']) == 2


def test_objects_queue_contains(q):
    q.fill('foo', {})
    assert q.contains('foo') is True
    assert q.contains('bar') is False


def test_objects_queue_size(q):
    q.fill('foo', {
        'type_foo': [],
        'type_bar': [-99],
    })
    assert q.size('foo', 'type_foo') == 0
    assert q.size('foo', 'type_bar') == 1
    with pytest.raises(KeyError):
        q.size('bar', '')


def test_objects_queue_pop(q):
    q.fill('foo', {
        'type_foo': [],
        'type_bar': [-99],
    })
    assert q.pop('foo', 'type_foo') is None
    assert q.pop('foo', 'type_bar') == -99
    with pytest.raises(KeyError):
        q.pop('bar', '')
