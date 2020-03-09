import threading


class ReadLock(object):
    """Context manager for a read lock attached to a given condition."""

    def __init__(self, condition):
        self._condition = condition

    def __enter__(self):
        self._condition.add_reader()

    def __exit__(self, type, value, traceback):
        self._condition.remove_reader()


class WriteLock(object):
    """Context manager for a write lock attached to a given condition."""

    def __init__(self, condition):
        self._condition = condition

    def __enter__(self):
        self._condition.add_writer()

    def __exit__(self, type, value, traceback):
        self._condition.remove_writer()


class ReadWriteCondition(object):
    def __init__(self):
        self._condition = threading.Condition(threading.Lock())
        self._readers = 0  # Number of readers: as long as it's not zero, it's not possible to write.

    def add_reader(self):
        """Takes the condition, then increments the reader count and releases the condition."""
        with self._condition:
            self._readers += 1

    def remove_reader(self):
        """Takes the condition, then decrements the reader count.
        If no readers are left, notifies all threads waiting on the condition.
        Then releases the condition."""
        with self._condition:
            self._readers -= 1
            if self._is_free():
                self._condition.notify_all()

    def add_writer(self):
        """Takes the condition, and waits until all current readers remove themselves.
        Then it's safe to write on the underlying object."""
        self._condition.acquire()
        while not self._is_free():
            self._condition.wait()

    def remove_writer(self):
        """Releases the condition, making the underlying object available for
        read or write operations."""
        self._condition.release()

    def _is_free(self):
        return self._readers == 0


class ReadWriteLock(object):
    """A lock object that allows many simultaneous "read locks", but
    only one "write lock." """

    def __init__(self):
        self._condition = ReadWriteCondition()

    def read_lock(self):
        """Generates a read lock context manager based on the shared condition."""
        return ReadLock(self._condition)

    def write_lock(self):
        """Generates a write lock context manager based on the shared condition."""
        return WriteLock(self._condition)
