import time

from .lock import ReadWriteLock

DEFAULT_SHARED_PROCESS_LIST_CACHE_DURATION = 120


class ProcessListCache(object):
    # Process list to be shared among all instances
    elements = []
    lock = ReadWriteLock()
    last_ts = 0
    cache_duration = DEFAULT_SHARED_PROCESS_LIST_CACHE_DURATION

    def read_lock(self):
        return self.lock.read_lock()

    def write_lock(self):
        return self.lock.write_lock()

    def should_refresh_proclist(self):
        now = time.time()
        return now - self.last_ts > self.cache_duration
