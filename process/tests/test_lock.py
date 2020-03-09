import threading
import time

import pytest

from datadog_checks.process.lock import ReadWriteLock

READER_SLEEP = 0.005


@pytest.mark.unit
def test_read_lock():
    lock = ReadWriteLock()

    with lock.read_lock():
        # Check that taking the lock does increase reader count
        assert lock._condition._readers == 1
        with lock.read_lock():
            # Check that multiple readers can coexist
            assert lock._condition._readers == 2

    assert lock._condition._readers == 0


@pytest.mark.unit
def test_read_write_lock():
    lock = ReadWriteLock()

    value = {'target': 0}

    def writer():
        for _ in range(1000):
            with lock.write_lock():
                value['target'] = value['target'] + 1

    def reader():
        for _ in range(1000):
            with lock.read_lock():
                read_target_value = value['target']
                time.sleep(READER_SLEEP)
                # Check that noone tried to write while the reader had the lock
                assert read_target_value == value['target']

    threads = []
    threads.append(threading.Thread(group=None, target=writer, name="writer"))
    threads.append(threading.Thread(group=None, target=reader, name="reader 1"))
    threads.append(threading.Thread(group=None, target=reader, name="reader 2"))
    for thread in threads:
        thread.start()
    while threads:
        time.sleep(0.5)
        threads = [x for x in threads if x.is_alive()]
    assert value['target'] == 1000


@pytest.mark.unit
def test_multi_write_lock():
    lock = ReadWriteLock()

    value = {'target': 0}

    def writer():
        for _ in range(1000):
            with lock.write_lock():
                value['target'] = value['target'] + 1

    def reader():
        for _ in range(1000):
            with lock.read_lock():
                read_target_value = value['target']
                time.sleep(READER_SLEEP)
                # Check that noone tried to write while the reader had the lock
                assert read_target_value == value['target']

    threads = []
    threads.append(threading.Thread(group=None, target=writer, name="writer 1"))
    threads.append(threading.Thread(group=None, target=writer, name="writer 2"))
    threads.append(threading.Thread(group=None, target=reader, name="reader 1"))
    threads.append(threading.Thread(group=None, target=reader, name="reader 2"))
    for thread in threads:
        thread.start()
    while threads:
        time.sleep(0.5)
        threads = [x for x in threads if x.is_alive()]
    assert value['target'] == 2000
