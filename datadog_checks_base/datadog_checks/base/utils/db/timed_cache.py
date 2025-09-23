# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time


class TimedCache:
    """
    A cache that expires after a given TTL. The cache can be used as a dictionary.

    Note: The cache DOES NOT automatically clear itself.
    It is up to the user to check if the cache is expired and clear it if needed.
    This is to avoid clearing the cache while it is being used in the middle of a check run.

    Example:
    ```
    cache = TimedCache(600)  # Cache expires after 10 minutes
    if cache.is_expired():  # Check if the cache is expired
        cache.clear()  # Clear the cache and reset the last refresh time
        # Do something to rebuild the cache

    cache['key'] = 'value'  # Set an item in the cache
    print(cache['key'])  # Get an item from the cache
    print(cache.get('mykey', 1))  # Get an item from the cache with a default value
    del cache['key']
    ```
    """

    def __init__(self, ttl):
        """Initialize the cache with a TTL for the entire cache."""
        self.__cache = {}
        self.__ttl = ttl
        self.__last_refresh_time = time.time()

    def __setitem__(self, key, value):
        """Set an item in the cache."""
        self.__cache[key] = value

    def __getitem__(self, key):
        """
        Get an item from the cache.
        Raise KeyError if the key is not found.
        """
        return self.__cache[key]

    def __delitem__(self, key):
        """Delete an item from the cache."""
        del self.__cache[key]

    def get(self, key, default=None):
        """Retrieve an item from the cache, returning default if the key is not found."""
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def is_expired(self):
        """Check if the cache is expired based on the TTL."""
        return (time.time() - self.__last_refresh_time) >= self.__ttl

    def clear(self):
        """Clear the entire cache and reset the last refresh time."""
        self.__cache = {}
        self.__last_refresh_time = time.time()
