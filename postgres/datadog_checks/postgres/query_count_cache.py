# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from cachetools import TTLCache

# 8 hours
CACHE_TTL = 60 * 60 * 8


class QueryCountCache:
    """Maintains a cache of the last-known number of calls per queryid"""

    def __init__(self):
        self.cache = TTLCache(
            maxsize=10000,
            ttl=CACHE_TTL,
        )
        self.update_counts = {}

    def set_calls(self, queryid, calls):
        """Updates the cache of calls per query id.

        Returns whether or not the number of calls changed based on
        the newly updated value. The first seen update for a queryid
        does not count as a change in values since that would result
        in an inflated value."""
        calls_changed = False
        if queryid in self.cache:
            diff = calls - self.cache[queryid]
            calls_changed = diff > 0

        self.cache[queryid] = calls

        return calls_changed
