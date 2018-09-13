# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import threading


class MetadataNotFoundError(Exception):
    pass


class MetadataCache:
    """
    Implements a thread safe storage for metrics metadata.
    For each instance key the cache maps: counter ID --> metric name, unit
    """
    def __init__(self):
        self._metadata = {}
        self._metadata_lock = threading.RLock()

    def init_instance(self, key):
        """
        Create an empty instance if it doesn't exist.
        If the instance already exists, this is a noop.
        """
        with self._metadata_lock:
            if key not in self._metadata:
                self._metadata[key] = {}

    def contains(self, key, counter_id):
        """
        Return whether a counter_id is present for a given instance key.
        If the key is not in the cache, raises a KeyError.
        """
        with self._metadata_lock:
            return counter_id in self._metadata[key]

    def set_metadata(self, key, metadata):
        """
        Store the metadata for the given instance key.
        """
        with self._metadata_lock:
            self._metadata[key] = metadata

    def get_metadata(self, key, counter_id):
        """
        Return the metadata for the metric identified by `counter_id` for the given instance key.
        If the key is not in the cache, raises a KeyError.
        If there's no metric with the given counter_id, raises a MetadataNotFoundError.
        """
        with self._metadata_lock:
            metadata = self._metadata[key]
            try:
                return metadata[counter_id]
            except KeyError:
                raise MetadataNotFoundError("No metadata for counter id '{}' found in the cache.".format(counter_id))
