# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import threading
import time

from datadog_checks.vsphere.legacy.common import REALTIME_RESOURCES


class MorNotFoundError(Exception):
    pass


class MorCache:
    """
    Implements a thread safe storage for Mor objects.
    For each instance key, the cache maps: mor_name --> mor_dict_object
    """

    def __init__(self, log):
        self._mor = {}
        self._mor_lock = threading.RLock()
        self.log = log

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
            for k, v in self._mor.get(key, {}).items():
                yield k, v

    def mors_batch(self, key, batch_size, max_historical_metrics=None):
        """
        Generator returning as many dictionaries containing `batch_size` Mor
        objects as needed to iterate all the content of the cache. This has
        to be iterated twice, like:

            for batch in cache.mors_batch('key', 100):
                for name, mor in batch:
                    # use the Mor object here
        If max_historical_metrics is specified, the function will also limit
        the size of the batch so that the integration never makes an API call
        with more than this given amount of historical metrics.
        """
        if max_historical_metrics is None:
            max_historical_metrics = float('inf')
        with self._mor_lock:
            mors_dict = self._mor.get(key) or {}

            batch = {}
            nb_hist_metrics = 0
            for mor_name, mor in mors_dict.items():
                if mor['mor_type'] not in REALTIME_RESOURCES and mor.get('metrics'):
                    # Those metrics are historical, let's make sure we don't have too
                    # many of them in the same batch.
                    if len(mor['metrics']) >= max_historical_metrics:
                        # Too many metrics to query for a single mor, ignore it
                        self.log.warning(
                            "Metrics for '%s' are ignored because there are more (%d) than what you allowed (%d) on vCenter Server",  # noqa: E501
                            mor_name,
                            len(mor['metrics']),
                            max_historical_metrics,
                        )
                        continue

                    nb_hist_metrics += len(mor['metrics'])
                    if nb_hist_metrics >= max_historical_metrics:
                        # Adding those metrics to the batch would make it too big, yield it now
                        self.log.info("Will request %d hist metrics", nb_hist_metrics - len(mor['metrics']))
                        yield batch
                        batch = {}
                        nb_hist_metrics = len(mor['metrics'])

                batch[mor_name] = mor

                if len(batch) == batch_size:
                    self.log.info("Will request %d hist metrics", nb_hist_metrics)
                    yield batch
                    batch = {}
                    nb_hist_metrics = 0

            if batch:
                self.log.info("Will request %d hist metrics", nb_hist_metrics)
                yield batch

    def legacy_mors_batch(self, key, batch_size, _=None):
        """
        FIXME: This has a bug with historical metrics. The `max_query_metrics` parameter on vcenter side limits
        the number of metrics that are queryable in the same request. The `mors_batch` method fixes that issue but is
        not yet enabled by default.

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

            mor_names = list(mors_dict)
            mor_names.sort()
            total = len(mor_names)
            for idx in range(0, total, batch_size):
                names_chunk = mor_names[idx : min(idx + batch_size, total)]
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
            for name, mor in self._mor[key].items():
                age = now - mor['creation_time']
                if age > ttl:
                    mors_to_purge.append(name)

            # ...then actually remove the Mors from the cache.
            for name in mors_to_purge:
                del self._mor[key][name]
