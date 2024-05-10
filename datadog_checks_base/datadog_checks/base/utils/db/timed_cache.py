# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading


class TimedCache:
    """A simple cache that clears itself every interval seconds."""

    def __init__(self, interval):
        """
        Initialize the cache with an interval in seconds.

        :param interval (int): The interval in seconds to clear the cache.
        """
        self.__cache = {}
        self.__interval = interval
        self.__timer = threading.Timer(self.__interval, self.__clear_cache)
        self.__timer.start()

    def __setitem__(self, key, value):
        """Set an item in the cache like dict[key] = value."""
        self.__cache[key] = value

    def __getitem__(self, key):
        """Get an item from the cache like value = dict[key]."""
        return self.__cache[key]

    def __delitem__(self, key):
        """Delete an item from the cache like del dict[key]."""
        del self.__cache[key]

    def __bool__(self):
        """Return True if the cache has any items, False otherwise."""
        return bool(self.__cache)

    def get(self, key, default=None):
        """Retrieve an item from the cache, returning default if key is not found."""
        return self.__cache.get(key, default)

    def __clear_cache(self):
        """Clear the cache and reset the timer."""
        self.__cache.clear()
        self.__timer = threading.Timer(self.__interval, self.__clear_cache)
        self.__timer.start()

    def stop(self):
        """Stop the timer if it's still running."""
        self.__timer.cancel()
