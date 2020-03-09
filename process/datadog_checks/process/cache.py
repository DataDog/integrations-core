import time

import psutil

from .lock import ReadWriteLock

DEFAULT_SHARED_PROCESS_LIST_CACHE_DURATION = 120


class ProcessListCache(object):
    """Process list to be shared among all instances."""

    elements = []
    lock = ReadWriteLock()
    last_ts = 0
    cache_duration = DEFAULT_SHARED_PROCESS_LIST_CACHE_DURATION

    def read_lock(self):
        return self.lock.read_lock()

    def write_lock(self):
        return self.lock.write_lock()

    def _should_refresh(self):
        now = time.time()
        return now - self.last_ts > self.cache_duration

    def refresh(self):
        """Checks if cache should be refreshed, and refreshes it if needed.
        Returns True if the cache was refreshed, False otherwise."""

        # Acquire the write lock to check whether to refresh because we're
        # going to keep it to do the refresh, AND, we don't want multiple
        # threads getting a `yes` result at once
        with self.write_lock():
            if self._should_refresh():
                self.elements = [proc for proc in psutil.process_iter(attrs=['pid', 'name'])]
                self.last_ts = time.time()
                return True
            else:
                return False
