# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
class QueryCallsCache:
    """Maintains a cache of the last-known number of calls per queryid, as per pg_stat_statements"""

    def __init__(self):
        self.cache = {}
        self.next_cache = {}
        self.called_queryids = []
        self.next_called_queryids = set()

    def end_query_call_snapshot(self):
        """To prevent evicted statements from building up in the cache we
        replace the cache outright after each sampling of pg_stat_statements."""
        self.cache = self.next_cache
        self.next_cache = {}
        self.called_queryids = self.next_called_queryids
        self.next_called_queryids = set()

    def set_calls(self, rows):
        """Updates the cache of calls per query id.

        Returns whether or not the number of calls changed based on
        the newly updated value. The first seen update for a queryid
        does not count as a change in values since that would result
        in an inflated value."""
        for row in rows:
            queryid = row['queryid']
            calls = row['calls']
            calls_changed = False

            if queryid in self.cache:
                diff = calls - self.cache[queryid]
                # Positive deltas mean the statement remained in pg_stat_statements
                # between check calls. Negative deltas mean the statement was evicted
                # and replaced with a new call count. Both cases should count as a call
                # change.
                calls_changed = diff != 0
            else:
                calls_changed = True

            self.next_cache[queryid] = calls
            if calls_changed:
                self.next_called_queryids.add(queryid)

        self.end_query_call_snapshot()
