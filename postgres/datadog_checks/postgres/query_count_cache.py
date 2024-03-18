# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from cachetools import TTLCache

# 1 hour
CACHE_TTL = 60 * 60


class QueryCountCache:
    """Maintains a cache of the last-known number of calls per queryid"""

    def __init__(self, maxsize):
        self.cache = TTLCache(
            maxsize=maxsize,
            ttl=CACHE_TTL,
        )

    def set_calls(self, queryid, calls):
        """Updates the cache of calls per query id.

        Returns whether or not the number of calls changed based on
        the newly updated value. The first seen update for a queryid
        does not count as a change in values since that would result
        in an inflated value."""
        calls_changed = False
        if queryid in self.cache:
            diff = calls - self.cache[queryid]
            # Positive deltas mean the statement remained in pg_stat_statements
            # between check calls. Negaitve deltas mean the statement was evicted
            # and replaced with a new call count. Both cases should count as a call
            # change.
            calls_changed = diff != 0
        else:
            calls_changed = True

        self.cache[queryid] = calls

        return calls_changed
