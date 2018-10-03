# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import threading
import time


class MorNotFoundError(Exception):
    pass


class MorCache:
    """
    Implements a thread safe storage for Mor objects.
    For each instance key, the cache maps: mor_name --> mor_dict_object
    """
    def __init__(self):
        self._mor = {}
        self._mor_lock = threading.RLock()

    def init_instance(self, key):
        """
        Create an empty instance if it doesn't exist.
        If the instance already exists, this is a noop.
        """
        with self._mor_lock:
            if key not in self._mor:
                self._mor[key] = {}

    def contains(self, key):
        """
        Return whether an instance key is present.
        """
        with self._mor_lock:
            return key in self._mor

    def instance_size(self, key):
        """
        Return how many Mor objects are stored for the given instance.
        If the key is not in the cache, raises a KeyError.
        """
        with self._mor_lock:
            return len(self._mor[key])

    def set_mor(self, key, name, mor):
        """
        Store a Mor object in the cache with the given name.
        If the key is not in the cache, raises a KeyError.
        """
        with self._mor_lock:
            self._mor[key][name] = mor
            self._mor[key][name]['creation_time'] = time.time()

    def get_mor(self, key, name):
        """
        Return the Mor object identified by `name` for the given instance key.
        If the key is not in the cache, raises a KeyError.
        If there's no Mor with the given name, raises a MorNotFoundError.
        """
        with self._mor_lock:
            mors = self._mor[key]
            try:
                return mors[name]
            except KeyError:
                raise MorNotFoundError("Mor object '{}' is not in the cache.".format(name))

    def set_metrics(self, key, name, metrics):
        """
        Store a list of metric identifiers for the given instance key and Mor
        object name.
        If the key is not in the cache, raises a KeyError.
        If the Mor object is not in the cache, raises a MorNotFoundError
        """
        with self._mor_lock:
            mor = self._mor[key].get(name)
            if mor is None:
                raise MorNotFoundError("Mor object '{}' is not in the cache.".format(name))
            mor['metrics'] = metrics

    def mors(self, key):
        """
        Generator returning all the mors in the cache for the given instance key.
        """
        with self._mor_lock:
            for k, v in self._mor.get(key, {}).iteritems():
                yield k, v

    def mors_batch(self, key, batch_size):
        """
        Generator returning as many dictionaries containing `batch_size` Mor
        objects as needed to iterate all the content of the cache. This has
        to be iterated twice, like:

            for batch in cache.mors_batch('key', 100):
                for name, mor in batch:
                    # use the Mor object here
        """
        with self._mor_lock:
            mors_dict = self._mor.get(key)
            if mors_dict is None:
                yield {}

            mor_names = mors_dict.keys()
            mor_names.sort()
            total = len(mor_names)
            for idx in range(0, total, batch_size):
                names_chunk = mor_names[idx:min(idx + batch_size, total)]
                yield {name: mors_dict[name] for name in names_chunk}

    def purge(self, key, ttl):
        """
        Remove all the items in the cache for the given key that are older than
        ttl seconds.
        If the key is not in the cache, raises a KeyError.
        """
        mors_to_purge = []
        now = time.time()
        with self._mor_lock:
            # Don't change the dict during iteration!
            # First collect the names of the Mors to remove...
            for name, mor in self._mor[key].iteritems():
                age = now - mor['creation_time']
                if age > ttl:
                    mors_to_purge.append(name)

            # ...then actually remove the Mors from the cache.
            for name in mors_to_purge:
                del self._mor[key][name]
